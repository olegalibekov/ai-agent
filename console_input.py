import json
import datetime as dt
from pathlib import Path

MESSAGES_FILE = Path("messages.json")


def load_messages() -> dict:
    if not MESSAGES_FILE.exists():
        return {"messages": []}
    with MESSAGES_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_messages(data: dict) -> None:
    with MESSAGES_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    print("=== Консольный ввод сообщений ===")
    print("Сообщения будут сохраняться в messages.json")
    print("Ctrl+C — выход\n")

    try:
        while True:
            text = input("> ").strip()
            if not text:
                continue

            data = load_messages()
            now = dt.datetime.now().strftime("%H:%M:%S")
            data["messages"].append(
                {
                    "time": now,
                    "text": text,
                }
            )
            save_messages(data)
    except KeyboardInterrupt:
        print("\nВыход из консольного ввода")


if __name__ == "__main__":
    main()
