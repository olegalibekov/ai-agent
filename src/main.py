import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

MODEL_NAME = "llama3.1:8b"
OLLAMA_URL = "http://localhost:11434/api/chat"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN не найден. Добавь его в .env или в переменные окружения.")

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def ask_ollama(prompt: str) -> str:
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "stream": False,
    }

    response = requests.post(OLLAMA_URL, json=payload, timeout=600)
    response.raise_for_status()
    data = response.json()
    return data["message"]["content"]


def send_message(chat_id: int, text: str, reply_to_message_id: int | None = None) -> None:
    # Ограничение Telegram — 4096 символов в сообщении
    for chunk_start in range(0, len(text), 4096):
        chunk = text[chunk_start:chunk_start + 4096]
        payload = {
            "chat_id": chat_id,
            "text": chunk,
        }
        if reply_to_message_id and chunk_start == 0:
            payload["reply_to_message_id"] = reply_to_message_id

        resp = requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload)
        resp.raise_for_status()


def get_updates(offset: int | None = None) -> list[dict]:
    params = {
        "timeout": 30,  # long polling
    }
    if offset is not None:
        params["offset"] = offset

    resp = requests.get(f"{TELEGRAM_API_URL}/getUpdates", params=params, timeout=35)
    resp.raise_for_status()
    data = resp.json()
    return data.get("result", [])


def handle_update(update: dict) -> None:
    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    chat_id = message["chat"]["id"]
    message_id = message["message_id"]
    text = message.get("text")

    if not text:
        send_message(chat_id, "Понимаю только текстовые сообщения 🙃", message_id)
        return

    # Простая обработка команд
    if text.startswith("/start"):
        send_message(
            chat_id,
            "Привет! Я бот, который отвечает с помощью локальной LLM через Ollama.\n"
            "Напиши мне любой вопрос 🙂",
            message_id,
        )
        return

    if text.startswith("/help"):
        send_message(
            chat_id,
            "Я использую локальную модель (Ollama) для ответа на твои сообщения.\n"
            "Просто напиши текст — я подумаю и отвечу.",
            message_id,
        )
        return

    # Можно сразу ответить, что думаем (опционально)
    thinking_msg = None
    try:
        thinking_resp = requests.post(
            f"{TELEGRAM_API_URL}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": "Думаю над ответом 🤔 (локальная модель)...",
                "reply_to_message_id": message_id,
            },
        )
        thinking_resp.raise_for_status()
        thinking_data = thinking_resp.json()
        thinking_msg = thinking_data.get("result", {}).get("message_id")
    except Exception:
        pass

    try:
        answer = ask_ollama(text)
    except Exception as e:
        send_message(chat_id, f"Ошибка при обращении к локальной модели:\n{e}", message_id)
        return

    send_message(chat_id, answer, message_id)


def main() -> None:
    print("Бот запущен. Ожидаю сообщения...")
    last_update_id: int | None = None

    while True:
        try:
            updates = get_updates(offset=last_update_id + 1 if last_update_id is not None else None)
            for update in updates:
                last_update_id = update["update_id"]
                handle_update(update)
        except KeyboardInterrupt:
            print("Останавливаю бота...")
            break
        except Exception as e:
            print(f"Ошибка в основном цикле: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
