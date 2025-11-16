#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, UTC
from typing import List, Literal

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ==========================
#  НАСТРОЙКИ
# ==========================

DB_PATH = "memory.db"
SESSION_ID = "default_session"

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

Role = Literal["user", "assistant", "system"]


@dataclass
class Message:
    id: int
    session_id: str
    role: Role
    content: str
    is_active: bool
    created_at: str


# ==========================
#  РАБОТА С БД
# ==========================

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );
        """
    )
    conn.commit()
    conn.close()


def save_message(session_id: str, role: Role, content: str) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO messages (session_id, role, content, is_active, created_at)
        VALUES (?, ?, ?, 1, ?)
        """,
        (
            session_id,
            role,
            content,
            datetime.now(UTC).isoformat(),
        ),
    )
    conn.commit()
    message_id = cur.lastrowid
    conn.close()
    return message_id


def fetch_active_messages(session_id: str) -> List[Message]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM messages
        WHERE session_id = ? AND is_active = 1
        ORDER BY id ASC
        """,
        (session_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return [
        Message(
            id=row["id"],
            session_id=row["session_id"],
            role=row["role"],
            content=row["content"],
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
        )
        for row in rows
    ]


# ==========================
#  ВЫЗОВ LLM ЧЕРЕЗ RESPONSES API
# ==========================

def _format_dialog_as_text(messages: List[Message]) -> str:
    """Сконвертировать историю в один текстовый промпт."""
    lines: List[str] = []

    # общий system-контекст
    lines.append(
        "Система: Ты русскоязычный ассистент. Отвечай по-русски, дружелюбно и по делу."
    )

    for m in messages:
        if m.role == "user":
            prefix = "Пользователь"
        elif m.role == "assistant":
            prefix = "Ассистент"
        else:
            prefix = "Система"

        lines.append(f"{prefix}: {m.content}")

    # попросим модель продолжить как ассистент
    lines.append("Ассистент:")

    return "\n".join(lines)


def call_llm(messages: List[Message]) -> str:
    """
    Вместо messages-формата используем один большой текстовый промпт.
    Так мы избегаем всех нюансов схемы input для Responses API.
    """
    prompt_text = _format_dialog_as_text(messages)

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt_text,
        # при желании можно указать max_output_tokens
        # max_output_tokens=512,
    )

    # в новом SDK есть удобный shortcut
    return response.output_text.strip()


# ==========================
#  ПЕЧАТЬ ИСТОРИИ
# ==========================

def print_full_history(session_id: str):
    messages = fetch_active_messages(session_id)

    print("\n================= ИСТОРИЯ ДИАЛОГА =================")
    if not messages:
        print("(история пуста)")
        print("===================================================\n")
        return

    for m in messages:
        date = m.created_at.split("T")[0] if "T" in m.created_at else m.created_at
        print(f"[{date}] {m.role.upper()}: {m.content}")

    print("===================================================\n")


# ==========================
#  ЧАТ-ЦИКЛ
# ==========================

def chat():
    init_db()
    print("Агент с долговременной памятью (SQLite + Responses API).")
    print("Введите сообщение. Для выхода — exit/quit.\n")

    # печатаем всю историю при запуске
    print_full_history(SESSION_ID)

    while True:
        user_input = input("Сообщение: ").strip()
        if user_input.lower() in ("exit", "quit"):
            print("Выход")
            break

        # сохраняем сообщение пользователя
        save_message(SESSION_ID, "user", user_input)

        # берём всю историю
        full_history = fetch_active_messages(SESSION_ID)

        # вызываем модель
        assistant_reply = call_llm(full_history)

        # сохраняем ответ ассистента
        save_message(SESSION_ID, "assistant", assistant_reply)

        # выводим в консоль
        print(f"Бот: {assistant_reply}\n")


if __name__ == "__main__":
    chat()
