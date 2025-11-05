import os
import json
import html
import logging
from collections import defaultdict, deque
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI, BadRequestError
from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ---------- Настройка ----------
logging.basicConfig(level=logging.INFO)
load_dotenv(dotenv_path=Path(__file__).with_name(".env"))

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not BOT_TOKEN or not OPENAI_API_KEY:
    raise RuntimeError("Укажи BOT_TOKEN и OPENAI_API_KEY в .env")

client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = (
    "You are a helpful assistant. "
    "Return only JSON with book information in the format:\n"
    "{'answer': {'title': '...', 'description': '...', 'author': '...'}}\n"
)

RESPONSE_JSON_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "BookInfoResponse",
        "schema": {
            "type": "object",
            "properties": {
                "answer": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "author": {"type": "string"},
                    },
                    "required": ["title", "description", "author"],
                }
            },
            "required": ["answer"],
        },
    },
}

# ---------- История сообщений ----------
HISTORY_LEN = 6
history: dict[int, deque] = defaultdict(lambda: deque(maxlen=HISTORY_LEN))

def make_messages(chat_id: int, user_text: str):
    """Собираем список сообщений: system + история + новое сообщение пользователя."""
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    msgs += list(history[chat_id])
    msgs.append({"role": "user", "content": user_text})
    return msgs

# ---------- Хэндлеры ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Напиши название книги 📚")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Очистка истории контекста."""
    history.pop(update.effective_chat.id, None)
    await update.message.reply_text("Контекст очищен. 🧹")

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    user_text = update.message.text.strip()

    try:
        messages = make_messages(chat_id, user_text)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            response_format=RESPONSE_JSON_SCHEMA,
        )

        data = json.loads(resp.choices[0].message.content)
        book = data["answer"]

        text = (
            f"<b>{html.escape(book['title'])}</b> — {html.escape(book['author'])}\n\n"
            f"{html.escape(book['description'])}"
        )

        # сохраняем в историю
        history[chat_id].append({"role": "user", "content": user_text})
        history[chat_id].append({"role": "assistant", "content": resp.choices[0].message.content})

    except BadRequestError as e:
        logging.error(e)
        text = "Ошибка запроса. Попробуй другое сообщение."
    except Exception as e:
        logging.error(e)
        text = "Что-то пошло не так 😕"

    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

# ---------- Основной запуск ----------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    logging.info("Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
