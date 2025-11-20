import os
import json
import asyncio
from dotenv import load_dotenv

from openai import OpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY is not set")

client = OpenAI(api_key=api_key)

SYSTEM_PROMPT = """
Ты агент, который может вызывать MCP-инструменты.
Всегда проверяй, можно ли решить задачу через инструменты.
Не давай финальный ответ, пока вся цепочка, нужная для решения задачи, не выполнена.
""".strip()


async def run_agent(user_query: str) -> None:
    # Запускаем локальный MCP-сервер
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_pipeline_server.py"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1. Получаем список MCP-тулов
            tools_response = await session.list_tools()

            # 2. Готовим tools для Responses API
            openai_tools: list = []
            for t in tools_response.tools:
                openai_tools.append(
                    {
                        "type": "function",
                        "name": t.name,
                        "description": t.description or "",
                        "parameters": t.inputSchema or {
                            "type": "object",
                            "properties": {},
                        },
                    }
                )

            # 3. Первый запрос к Responses API
            # Важный момент: здесь НЕТ role="tool"
            initial_prompt = f"{SYSTEM_PROMPT}\n\nЗапрос пользователя:\n{user_query}"

            response = client.responses.create(
                model="gpt-4.1-mini",
                input=initial_prompt,
                tools=openai_tools,
            )

            while True:
                tool_outputs: list = []

                # 4. Output: ищем function_call
                for item in response.output:
                    if item.type == "function_call":
                        tool_name = item.name
                        raw_args = item.arguments or "{}"

                        try:
                            args = json.loads(raw_args)
                        except json.JSONDecodeError:
                            args = {}
                            print(f"⚠️ Не удалось распарсить arguments: {raw_args}")

                        print(f"\n🛠  Вызов MCP-инструмента: {tool_name}({args})")

                        # Вызов MCP-тула по имени
                        mcp_result = await session.call_tool(tool_name, args)

                        # Достаём текстовый контент из ответа MCP
                        result_text_parts: list[str] = []
                        for part in mcp_result.content:
                            # FastMCP/стандартные части обычно имеют .text
                            txt = getattr(part, "text", None)
                            if txt:
                                result_text_parts.append(txt)
                            else:
                                result_text_parts.append(str(part))

                        result_text = "\n".join(result_text_parts).strip()

                        # 5. Добавляем function_call_output для Responses API
                        tool_outputs.append(
                            {
                                "type": "function_call_output",
                                "call_id": item.call_id,
                                "output": result_text,
                            }
                        )

                # Если модель НЕ запросила новых инструментов — это финальный ответ
                if not tool_outputs:
                    # Ищем последнее assistant-сообщение
                    final_text_parts: list[str] = []
                    for item in response.output:
                        if item.type == "message" and getattr(item, "role", None) == "assistant":
                            # item.content — список блоков, у каждого есть .text
                            for block in item.content:
                                txt = getattr(block, "text", None)
                                if txt:
                                    final_text_parts.append(txt)

                    final_answer = "\n".join(final_text_parts) if final_text_parts else "<empty answer>"

                    print("\n=== FINAL ANSWER ===\n")
                    print(final_answer)
                    break

                # 6. Отправляем выводы инструментов обратно в модель
                # previous_response_id сохраняет всё состояние (включая reasoning и т.д.)
                response = client.responses.create(
                    model="gpt-4.1-mini",
                    tools=openai_tools,
                    input=tool_outputs,
                    previous_response_id=response.id,
                )


if __name__ == "__main__":
    asyncio.run(
        run_agent(
            "Найди документы про ML, сделай суммаризацию и сохрани в файл result.txt"
        )
    )
