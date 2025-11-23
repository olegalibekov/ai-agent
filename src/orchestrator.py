# src/orchestrator.py
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
                            "Ты — ассистент-оркестратор. У тебя есть инструменты MCP от нескольких серверов.\n"
                            "- Если пользователь просит найти информацию в локальной базе — сначала вызови search-инструмент "
                            "(например, search_docs), чтобы получить сырые документы.\n"
                            "- Затем, если документов несколько или они длинные, вызови summarize-инструмент (summarize_text), "
                            "передав в него объединённый текст найденных документов.\n"
                            "- Уже по результату summarize дай пользователю краткий и понятный ответ.\n"
                            "- Если нужно что-то запомнить на будущее — используй reminder-инструменты.\n"
                            "Ты можешь вызывать несколько функций подряд в рамках одного диалога."
                        )

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

                # raw_args — то, как модель вернула аргументы (обычно строка JSON)
                raw_args = event.arguments or "{}"

                # Для MCP нужен dict → парсим
                if isinstance(raw_args, str):
                    try:
                        args: Dict[str, Any] = json.loads(raw_args)
                    except json.JSONDecodeError:
                        args = {}
                else:
                    args = raw_args

                # Вызов MCP-инструмента
                tool_result = await self._registry.call_tool(tool_name, args)

                # В **input** ОБЯЗАТЕЛЬНО вернуть и function_call, и function_call_output

                # 1) сам function_call (arguments ДОЛЖЕН быть строкой)
                conversation.append(
                    {
                        "type": "function_call",
                        "call_id": event.call_id,
                        "name": tool_name,
                        "arguments": raw_args if isinstance(raw_args, str) else json.dumps(raw_args),
                    }
                )

                # 2) результат
                conversation.append(
                    {
                        "type": "function_call_output",
                        "call_id": event.call_id,
                        "output": tool_result,
                    }
                )

                # и крутим цикл дальше
                continue

            # На всякий случай
            return f"Unsupported event type: {event.type}"
