# console_agent.py
import asyncio
import os
import sys
from contextlib import AsyncExitStack
from typing import Optional

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import OpenAI

# Модель можно заменить на другую быструю
MODEL_NAME = "gpt-4.1-mini"


# ---------- Инициализация OpenAI ----------
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("ОШИБКА: Нужно установить переменную среды OPENAI_API_KEY")

client = OpenAI(api_key=api_key)


class ConsoleReminderAgent:
    def __init__(self, server_script_path: str):
        self.server_script_path = server_script_path
        self.exit_stack = AsyncExitStack()
        self.session: Optional[ClientSession] = None
        self.running = True

    # ---------- Подключение к MCP-серверу ----------
    async def start(self):
        """Запускаем MCP-сервер (python reminder_mcp_server.py) и создаём сессию."""
        is_python = self.server_script_path.endswith(".py")
        if not is_python:
            raise ValueError("Ожидается .py файл MCP-сервера")

        server_params = StdioServerParameters(
            command=sys.executable,  # текущий python
            args=[self.server_script_path],
            env=None,
        )

        # stdio_client запускает сервер и отдаёт (read, write)
        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        read, write = stdio_transport

        self.session = await self.exit_stack.enter_async_context(
            ClientSession(read, write)
        )
        await self.session.initialize()

        # Просто выведем список инструментов MCP, чтобы убедиться что всё работает
        tools_resp = await self.session.list_tools()
        tool_names = [t.name for t in tools_resp.tools]
        print("Подключен MCP-сервер. Доступные инструменты:", ", ".join(tool_names))

    # ---------- Работа с MCP-инструментами ----------
    async def add_console_message(self, text: str):
        """Вызываем MCP-tool add_message(text=...)."""
        assert self.session is not None
        await self.session.call_tool("add_message", {"text": text})

    async def fetch_messages_text(self) -> str:
        """
        Вызывает MCP-tool get_messages и превращает результат в plain-text,
        который удобно скармливать LLM.
        """
        assert self.session is not None
        result = await self.session.call_tool("get_messages", {})

        # result.content — список элементов типа text/json/etc.
        # fastmcp при возврате dict делает JSON-контент.
        messages = []
        try:
            json_payload = None
            for item in result.content:
                if getattr(item, "type", None) == "json":
                    json_payload = item.data
            if json_payload is None:
                return "(не удалось разобрать результат MCP)"

            raw_msgs = json_payload.get("messages", [])
            for m in raw_msgs[-50:]:  # последние 50 сообщений достаточно
                time = m.get("time", "?")
                text = m.get("text", "")
                messages.append(f"{time}: {text}")
        except Exception as e:
            return f"(ошибка парсинга результата MCP: {e})"

        if not messages:
            return "(сообщений пока нет)"

        return "\n".join(messages)

    # ---------- Цикл суммаризации ----------
    async def summary_loop(self, interval_sec: int = 5):
        """
        Каждые interval_sec секунд:
        - берём сообщения через MCP
        - отправляем в OpenAI Responses API
        - печатаем summary
        """
        assert self.session is not None

        while self.running:
            try:
                msgs_text = await self.fetch_messages_text()
            except Exception as e:
                print(f"[summary_loop] Ошибка MCP: {e}")
                await asyncio.sleep(interval_sec)
                continue

            prompt = (
                "Ты делаешь короткие русскоязычные сводки сообщений пользователя.\n\n"
                "Вот сообщения за последнее время:\n"
                f"{msgs_text}\n\n"
                "Сделай краткое summary (1–3 предложения). "
                "Если сообщений нет или они пустые, скажи, что новых сообщений нет."
            )

            try:
                # Responses API
                resp = client.responses.create(
                    model=MODEL_NAME,
                    input=prompt,
                )

                # Собираем текст из output
                chunks = []
                for item in resp.output:
                    for content in item.content:
                        if content.type == "output_text":
                            chunks.append(content.text)
                summary_text = "".join(chunks).strip() or "[пустой ответ]"
            except Exception as e:
                summary_text = f"Ошибка запроса к LLM: {e}"

            print("\n========== SUMMARY ==========")
            print(summary_text)
            print("========== /SUMMARY =========\n")

            await asyncio.sleep(interval_sec)

    # ---------- Цикл ввода пользователя ----------
    async def input_loop(self):
        """
        Читаем сообщения из консоли и складываем их в MCP (add_message).
        """
        assert self.session is not None
        print("Вводи сообщения. /exit — выход.\n")

        while self.running:
            try:
                text = await asyncio.to_thread(input, "> ")
            except (EOFError, KeyboardInterrupt):
                self.running = False
                break

            text = text.strip()
            if not text:
                continue

            if text.lower() in ("/exit", "exit", "quit"):
                self.running = False
                break

            try:
                await self.add_console_message(text)
            except Exception as e:
                print(f"Ошибка add_message через MCP: {e}")

    # ---------- Запуск всего агента ----------
    async def run(self):
        await self.start()

        # параллельный таск суммаризации
        summary_task = asyncio.create_task(self.summary_loop(interval_sec=30))

        try:
            await self.input_loop()
        finally:
            self.running = False
            summary_task.cancel()
            try:
                await summary_task
            except asyncio.CancelledError:
                pass
            await self.exit_stack.aclose()


async def main():
    if len(sys.argv) < 2:
        print("Использование: python console_agent.py path/to/reminder_mcp_server.py")
        raise SystemExit(1)

    server_path = sys.argv[1]
    agent = ConsoleReminderAgent(server_path)
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
