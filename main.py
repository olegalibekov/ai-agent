import os
import time
import random
import logging
import traceback
import html
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
# Load .env next to this file, regardless of IDE cwd
load_dotenv(dotenv_path=Path(__file__).with_name(".env"))

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_FALLBACK_MODEL = os.getenv("OPENAI_FALLBACK_MODEL", "gpt-4o-mini")  # can be same or cheaper
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", "You are a helpful Telegram assistant. Keep replies concise.")
HISTORY_LEN = int(os.getenv("HISTORY_LEN", "6"))  # shorter = cheaper

if not BOT_TOKEN or not OPENAI_API_KEY:
    raise RuntimeError("BOT_TOKEN and OPENAI_API_KEY must be set in .env")

# ---------- OpenAI client ----------
client = OpenAI()  # reads OPENAI_API_KEY from env

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

def _try_openai(messages):
    """Try primary model, then fallback if quota/rate limits hit."""
    last_err = None
    for model in (OPENAI_MODEL, OPENAI_FALLBACK_MODEL):
        for attempt in range(3):
            try:
                return client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.6,
                )
            except RateLimitError as e:
                # if it's pure quota exhaustion, no point retrying too much
                if _is_insufficient_quota(e):
                    last_err = e
                    break
                # transient rate limit—backoff and retry
                last_err = e
                if attempt < 2:
                    _sleep_backoff(attempt)
                else:
                    break
            except (APIStatusError, BadRequestError, AuthenticationError) as e:
                # don't retry bad requests or auth errors
                last_err = e
                break
            except Exception as e:
                last_err = e
                break
        # if primary failed, try fallback model next loop
    raise last_err or RuntimeError("Unknown error calling OpenAI")

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    user_text = (update.message.text or "").strip()
    if not user_text:
        return

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    try:
        messages = make_messages(chat_id, user_text)

        completion = _try_openai(messages)
        reply = completion.choices[0].message.content.strip()

        # ---- log user text and model answer (raw) ----
        user_tag = f"{user.id} @{user.username or ''} {user.full_name or ''}".strip()
        logging.info("CHAT %s | msg_id=%s | user_text=%s", user_tag, update.message.message_id, user_text)
        logging.info("CHAT %s | reply=%s", user_tag, reply)

        # keep history (after success)
        history[chat_id].append({"role": "user", "content": user_text})
        history[chat_id].append({"role": "assistant", "content": reply})

        # send safe HTML
        safe_reply = html.escape(reply)
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
        # often invalid model, too-long context, or entity parsing issues
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
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
