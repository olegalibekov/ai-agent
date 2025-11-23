import json
from typing import Any, Dict, List

from openai import AsyncOpenAI

from tools_registry import ToolsRegistry


class Orchestrator:
    def __init__(self, client: AsyncOpenAI, tools_registry: ToolsRegistry, model: str) -> None:
        self._client = client
        self._registry = tools_registry
        self._model = model

    async def run_dialog(self, user_text: str) -> str:
        conversation: List[Dict[str, Any]] = [
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "Ты — ассистент-оркестратор с доступом к нескольким MCP-инструментам.\n"
                            "Правила:\n"
                            "1. Если пользователь спрашивает про документ, тему, концепт, технологию — всегда вызывай search_docs.\n"
                            "2. Не отвечай сам, пока не сделаешь вызов search_docs.\n"
                            "3. Затем вызывай summarize_text.\n"
                            "4. Не отвечай без вызова инструментов."
                        ),

                    }
                ],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": user_text}],
            },
        ]

        while True:
            response = await self._client.responses.create(
                model=self._model,
                input=conversation,
                tools=self._registry.tools_for_llm,
            )

            if not response.output:
                return "Empty response from model."

            event = response.output[0]

            # 1) Финальный текст
            if event.type == "message":
                return response.output_text or ""

            # 2) Вызов функции (инструмента)
            if event.type == "function_call":
                tool_name = event.name

                raw_args = event.arguments or "{}"
                if isinstance(raw_args, str):
                    try:
                        args: Dict[str, Any] = json.loads(raw_args)
                    except json.JSONDecodeError:
                        args = {}
                else:
                    args = raw_args

                tool_result = await self._registry.call_tool(tool_name, args)

                # 👉 Если это summarize_text — сразу возвращаем ровно то, что вернул тул
                if tool_name.endswith("___summarize_text"):
                    return tool_result

                conversation.append(
                    {
                        "type": "function_call",
                        "call_id": event.call_id,
                        "name": tool_name,
                        "arguments": raw_args if isinstance(raw_args, str) else json.dumps(raw_args),
                    }
                )

                conversation.append(
                    {
                        "type": "function_call_output",
                        "call_id": event.call_id,
                        "output": tool_result,
                    }
                )

                continue

            # На всякий случай
            return f"Unsupported event type: {event.type}"
