# src/servers/summarize_server.py

from mcp.server.fastmcp import FastMCP
import re

mcp = FastMCP("summarize-server", json_response=True)


@mcp.tool()
def summarize_text(text: str, max_sentences: int = 2) -> str:
    """
    Краткое изложение текста: оставляет первые N предложений.
    """
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    if not sentences:
        return ""
    return " ".join(sentences[:max_sentences])


if __name__ == "__main__":
    mcp.run()
