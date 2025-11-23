# src/servers/summarize_server.py

import os
import re

from mcp.server.fastmcp import FastMCP
from openai import OpenAI
from dotenv import load_dotenv  # <-- добавили

# грузим .env относительно текущей рабочей директории/проекта
load_dotenv()

mcp = FastMCP("summarize-server", json_response=True)

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

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "Ты делаешь краткое резюме текста.\n"
                            "Всегда отвечай строго одним законченным предложением на русском языке, "
                            "не больше и не меньше одного предложения."
                        ),
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": f"Суммаризируй этот текст в одно предложение:\n\n{text}",
                    }
                ],
            },
        ],
    )

    summary = (response.output_text or "").strip()

    # Жёстко обрежем по первому .?!, чтобы точно одно предложение
    m = re.search(r"[.!?]", summary)
    if not m:
        return summary
    end = m.end()
    return summary[:end].strip()


if __name__ == "__main__":
    mcp.run()
