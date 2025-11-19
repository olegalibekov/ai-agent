import os
import time
import json
import datetime as dt
from pathlib import Path
from typing import Dict, Any, List

from openai import OpenAI

from dotenv import load_dotenv

load_dotenv()

MESSAGES_FILE = Path("messages.json")

SUMMARY_INTERVAL_SECONDS = 5
MODEL_NAME = "gpt-4.1-mini"

# === Ключ только из ENV ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("ОШИБКА: установи переменную среды OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)


def load_messages() -> Dict[str, Any]:
    if not MESSAGES_FILE.exists():
        return {"messages": []}
    with MESSAGES_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_prompt(messages: List[Dict[str, str]]) -> str:
    if not messages:
        return "Сообщений пока нет. Скажи кратко, что данных для суммаризации ещё нет."

    lines = [f"[{m['time']}] {m['text']}" for m in messages]

    return (
            "Ниже список сообщений, которые пользователь вводил в консоль.\n"
            "Сделай короткое summary по-русски:\n"
            "— о чём в целом речь\n"
            "— какие основные мысли\n"
            "— если уместно, предложи следующий шаг.\n\n"
            "Сообщения:\n" +
            "\n".join(lines)
    )


def summarize_once():
    data = load_messages()
    messages = data.get("messages", [])

    prompt = build_prompt(messages)

    try:
        resp = client.responses.create(
            model=MODEL_NAME,
            input=prompt,
        )
        summary_text = resp.output_text
    except Exception as e:
        print(f"\n[SUMMARY ERROR] Ошибка при запросе к модели: {e}\n")
        return

    print("\n" + "=" * 60)
    print(f"[{dt.datetime.now().strftime('%H:%M:%S')}] SUMMARY:")
    print(summary_text)
    print("=" * 60 + "\n")


def main():
    print("=== Summary-агент запущен ===")
    print(f"Каждые {SUMMARY_INTERVAL_SECONDS} секунд будет печататься сводка.\n")

    try:
        while True:
            summarize_once()
            time.sleep(SUMMARY_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\nВыход из summary-цикла")


if __name__ == "__main__":
    main()
