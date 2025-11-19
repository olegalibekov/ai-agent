# reminder_mcp_server.py
import json
from pathlib import Path
from typing import Dict, List, Any

from mcp.server.fastmcp import FastMCP

MESSAGES_FILE = Path("messages.json")

mcp = FastMCP("console-reminder")


def _load_messages() -> Dict[str, List[Dict[str, str]]]:
    """Читаем messages.json (если нет — возвращаем пустой список)."""
    if not MESSAGES_FILE.exists():
        return {"messages": []}
    with MESSAGES_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def _save_messages(data: Dict[str, List[Dict[str, str]]]) -> None:
    """Сохраняем messages.json."""
    with MESSAGES_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@mcp.tool()
def add_message(text: str) -> str:
    """
    Инструмент MCP:
    Добавляет сообщение в локальный JSON.

    Аргументы:
      text: текст сообщения от пользователя.
    """
    from datetime import datetime

    data = _load_messages()
    data["messages"].append(
        {
            "time": datetime.now().isoformat(timespec="seconds"),
            "text": text,
        }
    )
    _save_messages(data)
    return "ok"


@mcp.tool()
def get_messages() -> Dict[str, List[Dict[str, str]]]:
    """
    Инструмент MCP:
    Возвращает все сообщения из JSON.

    Формат:
    {
      "messages": [
        {"time": "...", "text": "..."},
        ...
      ]
    }
    """
    return _load_messages()


if __name__ == "__main__":
    # Старт MCP-сервера (по stdio).
    mcp.run()
