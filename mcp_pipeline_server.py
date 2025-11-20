# mcp_pipeline_server.py
import os
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("pipeline-server")

# --- 1: searchDocs ---
@mcp.tool()
async def search_docs(query: str) -> str:
    """
    Ищет текст в "документах". Для примера — просто возвращает строку.
    """
    fake_documents = {
        "python": "Python — популярный язык с простым синтаксисом.",
        "flutter": "Flutter — фреймворк для кроссплатформенной разработки.",
        "ml": "Machine Learning — направление ИИ, использующее статистику."
    }

    result = [text for k, text in fake_documents.items() if query.lower() in k.lower()]
    return "\n".join(result) if result else "Ничего не найдено."


# --- 2: summarize ---
@mcp.tool()
async def summarize_text(text: str) -> str:
    """
    Упрощённая суммаризация.
    """
    if not text.strip():
        return "Нет текста для суммаризации."
    return "Краткое резюме: " + text[:100] + "..."


# --- 3: saveToFile ---
@mcp.tool()
async def save_to_file(filename: str, content: str) -> str:
    """
    Сохраняет данные в файл.
    """
    path = os.path.join(os.getcwd(), filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Сохранено в файл {path}"


if __name__ == "__main__":
    mcp.run()
