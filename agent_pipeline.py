# agent_pipeline.py

import os
import json
import asyncio
from dotenv import load_dotenv

from openai import OpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)

SYSTEM_PROMPT = """
Ты агент, который может вызывать MCP-инструменты.
Всегда проверяй, можно ли решить задачу через инструменты.
Не отвечай, пока последовательность вызовов tools не завершена.
"""


async def run_agent(user_query: str):
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_pipeline_server.py"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1) Получаем MCP-тулы
            tools_response = await session.list_tools()

            # 2) Конвертируем MCP-тулы в формат OpenAI tools
            openai_tools = []
            for t in tools_response.tools:
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description or "",
                        # MCP уже отдает JSON Schema для параметров
                        "parameters": t.inputSchema or {
                            "type": "object",
                            "properties": {},
                        },
                    },
                })

            messages: list[dict] = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_query},
            ]

            while True:
                # 3) Вызов LLM с tool
                response = client.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=messages,
                    tools=openai_tools,
                )

                ai_msg = response.choices[0].message

                # Сохраняем ход мысли модели (как обычное message)
                messages.append(ai_msg.model_dump(exclude_none=True))

                # 4) Если модель не запросила инструментов — финальный ответ
                if not ai_msg.tool_calls:
                    print("\n=== FINAL ANSWER ===\n")
                    print(ai_msg.content)
                    break

                # 5) Иначе — выполняем все tool_calls последовательно
                for tool_call in ai_msg.tool_calls:
                    tool_name = tool_call.function.name
                    raw_args = tool_call.function.arguments or "{}"

                    try:
                        args = json.loads(raw_args)
                    except json.JSONDecodeError:
                        args = {}
                        print(f"⚠️ Не удалось распарсить arguments: {raw_args}")

                    print(f"\n🛠  Вызов MCP-инструмента: {tool_name}({args})")

                    # вызов MCP-инструмента
                    tool_result = await session.call_tool(tool_name, args)

                    # приводим ответ от MCP к строке
                    result_str = ""
                    # MCP может вернуть список/структуру — возьмем текстовое содержимое
                    for part in tool_result.content:
                        if hasattr(part, "text") and part.text:
                            result_str += part.text + "\n"
                        else:
                            result_str += str(part) + "\n"

                    # 6) Прокидываем результат обратно в LLM
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,  # важно
                        "name": tool_name,
                        "content": result_str.strip(),
                    })


if __name__ == "__main__":
    asyncio.run(
        run_agent(
            "Найди документы про Flutter, сделай суммаризацию и сохрани в файл result.txt"
        )
    )
