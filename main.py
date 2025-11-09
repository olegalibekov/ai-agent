import os
import html
import logging
from collections import defaultdict, deque
from asyncio import Lock
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from openai.types.responses import Response

from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# -------------------- Настройка --------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
load_dotenv(dotenv_path=Path(__file__).with_name(".env"))

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", "You are a helpful assistant.")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # при желании поменяйте

if not BOT_TOKEN or not OPENAI_API_KEY:
    raise RuntimeError("Укажи BOT_TOKEN и OPENAI_API_KEY в .env")

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# -------------------- Диалоговое состояние --------------------
HISTORY_LEN = int(os.getenv("HISTORY_LEN", "10"))  # глубина истории по чату
history: dict[int, deque[str]] = defaultdict(lambda: deque(maxlen=HISTORY_LEN))
user_locks: dict[int, Lock] = {}


def make_model_input(chat_id: int, user_text: str) -> str:
    """
    Собираем компактный контекст:
    - последние реплики (user/assistant) в плоском виде
    - текущий запрос пользователя
    Это простой и устойчивый способ давать модели историю в Responses API.
    """
    lines = []
    for i, turn in enumerate(history[chat_id]):
        lines.append(turn)
    lines.append(f"User: {user_text}")
    return "\n".join(lines).strip()


def push_turn(chat_id: int, role: str, text: str) -> None:
    role = "User" if role == "user" else "Assistant"
    history[chat_id].append(f"{role}: {text}")


# -------------------- Хэндлеры --------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    history[chat_id].clear()
    await update.message.reply_text(
        "Привет! Я чат-бот с ChatGPT 🤖\n"
        "Напиши мне что-нибудь — отвечу в том же диалоге.\n\n"
        "Команды:\n"
        "/reset — очистить контекст\n"
        "/help — подсказка"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Я передаю твои сообщения в ChatGPT через Responses API.\n"
        "Можно менять системную роль через переменную SYSTEM_PROMPT в .env.\n\n"
        "Команды:\n"
        "/start — начать заново\n"
        "/reset — очистить контекст"
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    history[chat_id].clear()
    await update.message.reply_text("Контекст очищен 🧹")


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = (update.message.text or "").strip()
    if not text:
        return

    if chat_id not in user_locks:
        user_locks[chat_id] = Lock()
    lock = user_locks[chat_id]
    if lock.locked():
        # защищаем от дублирования при быстрых отправках
        return

    async with lock:
        await context.bot.send_chat_action(chat_id, ChatAction.TYPING)
        try:
            # Подготовим ввод для модели
            push_turn(chat_id, "user", text)
            model_input = make_model_input(chat_id, text)

            # Вызов Responses API
            # Важно: не задаём temperature (некоторые модели принимают только дефолт)
            resp: Response = await client.responses.create(
                model=OPENAI_MODEL,
                instructions=SYSTEM_PROMPT,  # ← системная роль
                input=model_input,  # ← строка с контекстом/сообщением
                max_output_tokens=700,
            )
            answer = (resp.output_text or "").strip()

            if not answer:
                answer = "🤔 Не удалось получить ответ. Попробуй спросить иначе."

            push_turn(chat_id, "assistant", answer)
            await update.message.reply_text(answer, parse_mode=ParseMode.HTML)

        except Exception as e:
            logging.exception(e)
            await update.message.reply_text("Упс, что-то пошло не так. Попробуй ещё раз позже 🙏")


# -------------------- Запуск --------------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    logging.info("Бот запущен")
    app.run_polling()


if __name__ == "__main__":
    main()
