# src/servers/summarize_server.py

import os
import re

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from openai import OpenAI

# Подтягиваем переменные из .env (в т.ч. OPENAI_API_KEY)
load_dotenv()

mcp = FastMCP("summarize-server", json_response=True)

# Клиент OpenAI: ключ берём из окружения
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


@mcp.tool()
def summarize_text(text: str) -> str:
    """
    Краткое изложение текста через OpenAI Responses API:
    возвращает строго одно законченное предложение.
    """
    text = text.strip()
    if not text:
        return ""

    # Делать сложную структуру input не нужно — используем instructions + input
    response = client.responses.create(
        model="gpt-4.1-mini",  # или твоя модель
        instructions=(
            "Ты делаешь краткое резюме текста.\n"
            "Всегда отвечай строго одним законченным предложением на русском языке, "
            "не больше и не меньше одного предложения."
        ),
        input=f"Суммаризируй этот текст в одно предложение:\n\n{text}",
    )

    summary = (response.output_text or "").strip()

    m = re.search(r"[.!?]", summary)
    if not m:
        return summary
    end = m.end()
    return summary[:end].strip()


if __name__ == "__main__":
    mcp.run()
