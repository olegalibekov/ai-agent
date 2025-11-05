import os
import time
import random
import logging
import traceback
import html
import json
from collections import defaultdict, deque
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from openai import RateLimitError, APIStatusError, AuthenticationError, BadRequestError

from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ---------- Logging ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

# ---------- Env ----------
load_dotenv(dotenv_path=Path(__file__).with_name(".env"))

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_FALLBACK_MODEL = os.getenv("OPENAI_FALLBACK_MODEL", "gpt-4o-mini")

# Короткий system-промпт (основное ограничение формата обеспечит JSON Schema ниже)
SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    (
        "You are a helpful Telegram assistant. Keep replies concise.\n"
        "Always respond with a JSON object that matches the provided JSON Schema."
    ),
)

HISTORY_LEN = int(os.getenv("HISTORY_LEN", "6"))

if not BOT_TOKEN or not OPENAI_API_KEY:
    raise RuntimeError("BOT_TOKEN and OPENAI_API_KEY must be set in .env")

# ---------- OpenAI client ----------
client = OpenAI()  # reads OPENAI_API_KEY from env

# ---------- Structured Outputs JSON Schema ----------
# В этой версии SDK 'required' должен включать все свойства. Даём дефолты, чтобы модель всегда была валидной.
RESPONSE_JSON_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "TelegramReply",
        "schema": {
            "type": "object",
            "properties": {
                "answer":    {"type": "string", "default": ""},
                "notes":     {"type": "string", "default": ""},
                "citations": {"type": "array", "items": {"type": "string"}, "default": []}
            },
            "required": ["answer", "notes", "citations"],
            "additionalProperties": False
        },
        "strict": True
    }
}

# ---------- In-memory conversation state (per chat) ----------
history: dict[int, deque] = defaultdict(lambda: deque(maxlen=HISTORY_LEN))

def make_messages(chat_id: int, user_text: str):
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    msgs += list(history[chat_id])
    msgs.append({"role": "user", "content": user_text})
    return msgs

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi! Send me a message and I’ll ask ChatGPT for you. ✨")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    history.pop(update.effective_chat.id, None)
    await update.message.reply_text("Context cleared. 🧹")

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("pong")

def _sleep_backoff(attempt: int):
    time.sleep(min(2 ** attempt + random.random(), 8))

def _is_insufficient_quota(err: Exception) -> bool:
    try:
        resp = getattr(err, "response", None)
        data = resp.json() if resp and hasattr(resp, "json") else {}
        code = (data.get("error") or {}).get("code")
        return code == "insufficient_quota"
    except Exception:
        return False

def _to_responses_input(messages):
    """
    Convert chat-like [{'role','content': str}] into Responses API format.
    role -> type mapping:
      - user/system -> input_text
      - assistant   -> output_text
    """
    converted = []
    for m in messages:
        role = m.get("role", "user")
        text = m.get("content", "")
        if not isinstance(text, str):
            text = str(text)
        content_type = "output_text" if role == "assistant" else "input_text"
        converted.append({
            "role": role,
            "content": [{"type": content_type, "text": text}],
        })
    return converted

def _try_openai(messages):
    """
    Try primary model, then fallback if quota/rate limits hit.
    Prefers Responses API + JSON Schema. If this SDK build doesn't support
    response_format in Responses API, falls back to Chat Completions API.
    Returns either dict (parsed JSON) or str.
    """
    last_err = None

    # Подготовим payload’ы под оба эндпоинта
    responses_input = _to_responses_input(messages)  # for Responses API
    chat_input = [{"role": m["role"], "content": m["content"]} for m in messages]  # for Chat Completions

    for model in (OPENAI_MODEL, OPENAI_FALLBACK_MODEL):
        # ---- 1) Попытка через Responses API (предпочтительно) ----
        try:
            resp = client.responses.create(
                model=model,
                input=responses_input,
                temperature=0.6,
                response_format=RESPONSE_JSON_SCHEMA,  # может быть не поддержан в твоём билде
            )
            text = getattr(resp, "output_text", None)
            if not text:
                # запасной парсер
                chunks = []
                for item in getattr(resp, "output", []) or []:
                    for c in getattr(item, "content", []) or []:
                        t = getattr(c, "text", None)
                        if t:
                            chunks.append(t)
                text = "".join(chunks).strip() if chunks else None
            if not text:
                raise RuntimeError("No text from Responses API")

            try:
                return json.loads(text)
            except Exception:
                return text

        except TypeError as e:
            # Ключевой случай: "unexpected keyword argument 'response_format'"
            if "response_format" in str(e):
                # ---- 2) Фолбэк: Chat Completions API с тем же response_format ----
                try:
                    chat_resp = client.chat.completions.create(
                        model=model,
                        messages=chat_input,
                        temperature=0.6,
                        response_format=RESPONSE_JSON_SCHEMA,
                    )
                    text = chat_resp.choices[0].message.content if chat_resp.choices else ""
                    if not text:
                        raise RuntimeError("No text from Chat Completions")

                    try:
                        return json.loads(text)
                    except Exception:
                        return text
                except Exception as e2:
                    last_err = e2
                    break  # нет смысла ретраить
            else:
                last_err = e
                break

        except RateLimitError as e:
            if _is_insufficient_quota(e):
                last_err = e
                break
            last_err = e
            _sleep_backoff(0)
            continue
        except (APIStatusError, BadRequestError, AuthenticationError) as e:
            last_err = e
            break
        except Exception as e:
            last_err = e
            break

    raise last_err or RuntimeError("Unknown error calling OpenAI API")

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    user_text = (update.message.text or "").strip()
    if not user_text:
        return

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    try:
        messages = make_messages(chat_id, user_text)
        model_reply = _try_openai(messages)

        # Если пришёл dict (валидный JSON по схеме), достаём answer/notes/citations
        if isinstance(model_reply, dict):
            answer_text = model_reply.get("answer", "").strip()
            notes = model_reply.get("notes", "")
            citations = model_reply.get("citations", [])
            logging.info("JSON reply parsed | notes=%s | citations=%s", notes, citations)
            assistant_text_for_history = answer_text
            text_to_send = answer_text or "(empty answer)"
        else:
            # Фолбэк: обычный текст
            assistant_text_for_history = str(model_reply)
            text_to_send = assistant_text_for_history

        user_tag = f"{user.id} @{user.username or ''} {user.full_name or ''}".strip()
        logging.info("CHAT %s | msg_id=%s | user_text=%s", user_tag, update.message.message_id, user_text)
        logging.info("CHAT %s | reply=%s", user_tag, assistant_text_for_history)

        # В историю кладём человекочитаемый ответ ассистента
        history[chat_id].append({"role": "user", "content": user_text})
        history[chat_id].append({"role": "assistant", "content": assistant_text_for_history})

        safe_reply = html.escape(text_to_send)
        await update.message.reply_text(safe_reply, parse_mode=ParseMode.HTML)

    except RateLimitError as e:
        if _is_insufficient_quota(e):
            msg = "The assistant hit an account quota limit. Please try again later or switch to a lower-cost model."
        else:
            msg = "I’m being rate-limited right now. Please try again in a bit."
        logging.error("RateLimitError: %s\n%s", e, traceback.format_exc())
        await update.message.reply_text(msg)

    except AuthenticationError as e:
        logging.error("AuthenticationError: %s\n%s", e, traceback.format_exc())
        await update.message.reply_text("Auth error with the AI provider. Check the API key on the server.")

    except BadRequestError as e:
        logging.error("BadRequestError: %s\n%s", e, traceback.format_exc())
        await update.message.reply_text("Request was rejected by the AI API (bad request). Try shorter input or /reset.")

    except APIStatusError as e:
        logging.error("APIStatusError: %s\n%s", e, traceback.format_exc())
        await update.message.reply_text("AI provider is temporarily unavailable. Please try again.")

    except Exception as e:
        logging.error("Unhandled error: %s\n%s", e, traceback.format_exc())
        await update.message.reply_text("Oops, something went wrong. Try again!")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    logging.info("Application started")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
