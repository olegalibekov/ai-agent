import os
import json
import html
import logging
import re
from pathlib import Path
from collections import defaultdict
from asyncio import Lock
from dotenv import load_dotenv
from openai import AsyncOpenAI, BadRequestError
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

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# ---------- Промпт ----------
SYSTEM_PROMPT = (
    "Ты помогаешь пользователю подобрать книгу.\n"
    "Ты должен собрать три поля:\n"
    "1) О чём должна быть книга (описание);\n"
    "2) Годы написания (точный год, диапазон или век);\n"
    "3) Страна автора.\n\n"
    "Когда всё собрано, верни СТРОГО JSON-объект:\n"
    "{\n"
    "  'state': 'final',\n"
    "  'title': '...',\n"
    "  'author': '...',\n"
    "  'description': '...',\n"
    "  'subject': '...',\n"
    "  'author_country': '...',\n"
    "  'publication_year': 1234\n"
    "}\n"
    "Не включай в ответ поле years_written."
)

user_data = defaultdict(lambda: {"content_summary": None, "years_written": None, "author_country": None})
user_locks: dict[int, Lock] = {}


# ---------- Парсинг годов и веков ----------
def parse_years(text: str):
    text = text.lower().replace("–", "-").replace("—", "-").replace("веке", "век")
    match_num_cent = re.search(r"(\d{1,2})\s*век", text)
    if match_num_cent:
        c = int(match_num_cent.group(1))
        return {"start_year": (c - 1) * 100, "end_year": (c - 1) * 100 + 99}
    match_roman = re.search(r"\b([xivlcdm]+)\s*век", text)
    if match_roman:
        roman = match_roman.group(1).upper()
        roman_map = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
        total, prev = 0, 0
        for ch in reversed(roman):
            val = roman_map.get(ch, 0)
            total = total - val if val < prev else total + val
            prev = val
        return {"start_year": (total - 1) * 100, "end_year": (total - 1) * 100 + 99}
    years = [int(x) for x in re.findall(r"\d{3,4}", text)]
    if len(years) == 1:
        return {"start_year": years[0], "end_year": None}
    if len(years) >= 2:
        return {"start_year": years[0], "end_year": years[1]}
    return None


# ---------- Проверка страны ----------
async def is_country_name_async(text: str) -> str | None:
    try:
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Определи, обозначает ли ответ название страны. "
                        "Пользователь отвечает на вопрос: 'Укажи страну автора'. "
                        "Верни строго JSON:\n"
                        '{"is_country": true/false, "name": "..." }'
                    ),
                },
                {"role": "user", "content": text.strip()},
            ],
            temperature=0,
            max_tokens=50,
            response_format={"type": "json_object"},
        )
        msg = resp.choices[0].message.content
        data = json.loads(msg)
        if data.get("is_country") and data.get("name"):
            return data["name"]
    except Exception as e:
        logging.warning(f"Country detection error: {e}")
    return None


# ---------- Рендер ----------
def render_final(book: dict) -> str:
    title = html.escape(book.get("title", ""))
    author = html.escape(book.get("author", ""))
    desc = html.escape(book.get("description", ""))
    subj = html.escape(book.get("subject", ""))
    country = html.escape(book.get("author_country") or "")
    c_line = f"\nСтрана автора: {country}" if country else ""
    pub = book.get("publication_year")
    p_line = f"\nГод публикации: {pub}" if isinstance(pub, int) else ""
    return f"<b>{title}</b> — {author}\n<i>{subj}</i>\n\n{desc}{c_line}{p_line}"


# ---------- Хэндлеры ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_chat.id] = {"content_summary": None, "years_written": None, "author_country": None}
    await update.message.reply_text("Привет! Расскажи, о чём должна быть книга 📚")


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data.pop(update.effective_chat.id, None)
    await update.message.reply_text("Контекст очищен 🧹")


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in user_locks:
        user_locks[chat_id] = Lock()
    lock = user_locks[chat_id]
    if lock.locked():
        return

    async with lock:
        await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
        text = update.message.text.strip()
        data = user_data[chat_id]

        if data["content_summary"] is None and len(text.split()) > 3:
            data["content_summary"] = text
        if data["years_written"] is None:
            years = parse_years(text)
            if years:
                data["years_written"] = years
        if data["author_country"] is None:
            country = await is_country_name_async(text)
            if country:
                data["author_country"] = country

        missing = [k for k, v in data.items() if v is None]

        if not missing:
            await update.message.reply_text("Спасибо! Сейчас подберу книгу 📖")
            try:
                prompt = (
                    f"Описание: {data['content_summary']}\n"
                    f"Годы написания: {data['years_written']}\n"
                    f"Страна автора: {data['author_country']}\n\n"
                    f"Подбери подходящую книгу и верни JSON согласно system prompt."
                )
                resp = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=300,
                    temperature=0.4,
                    response_format={"type": "json_object"},
                )
                msg = resp.choices[0].message.content
                book = json.loads(msg)
                if book.get("state") == "final":
                    await update.message.reply_text(render_final(book), parse_mode=ParseMode.HTML)
                else:
                    await update.message.reply_text("Не удалось получить финальный ответ 😕")
            except BadRequestError:
                await update.message.reply_text("Ошибка запроса. Попробуй другое сообщение.")
            except Exception as e:
                logging.exception(e)
                await update.message.reply_text("Что-то пошло не так 😕")
            finally:
                user_data.pop(chat_id, None)
            return

        if "content_summary" in missing:
            await update.message.reply_text("О чём должна быть книга?")
        elif "years_written" in missing:
            await update.message.reply_text("Укажи годы написания (например, 1980–1990, XIX век или 20 век).")
        elif "author_country" in missing:
            await update.message.reply_text("Теперь укажи страну автора.")


# ---------- Запуск ----------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    logging.info("Бот запущен")
    app.run_polling()


if __name__ == "__main__":
    main()
