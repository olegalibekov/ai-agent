"""
God Agent - Универсальный AI-ассистент
Объединяет MCP, RAG, голосовой ввод и Claude API
ИСПРАВЛЕННАЯ ВЕРСИЯ с абсолютными импортами
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

import yaml
from anthropic import Anthropic
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

# Абсолютные импорты вместо относительных
from voice_module import VoiceInterface
from rag_engine_ollama import RAGEngine
from mcp_manager import MCPManager
from memory import MemoryManager
from task_tracker import TaskTracker


@dataclass
class AgentContext:
    """Контекст текущего взаимодействия"""
    user_id: str
    session_id: str
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    current_task: Optional[str] = None
    context_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class GodAgent:
    """Главный класс God Agent"""

    def __init__(self, config_path: str = "config.yaml"):
        self.console = Console()
        self.logger = self._setup_logging()

        # Загрузка конфигурации
        self.config = self._load_config(config_path)

        # Инициализация компонентов
        self.anthropic = Anthropic()
        self.voice = VoiceInterface(self.config['voice']) if self.config['voice']['enabled'] else None
        self.rag = RAGEngine(self.config['rag'])
        self.mcp = MCPManager(self.config['mcp'])
        self.memory = MemoryManager(self.config['memory'])
        self.tasks = TaskTracker()

        # Контекст агента
        self.context = AgentContext(
            user_id="oleg",
            session_id=self._generate_session_id()
        )

        self.logger.info("God Agent initialized successfully")

    def _setup_logging(self) -> logging.Logger:
        """Настройка логирования"""
        logger = logging.getLogger("GodAgent")
        logger.setLevel(logging.INFO)

        # Создание директории для логов
        log_dir = Path("./logs")
        log_dir.mkdir(exist_ok=True)

        # File handler
        fh = logging.FileHandler(log_dir / "god_agent.log")
        fh.setLevel(logging.INFO)

        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)

        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        logger.addHandler(fh)
        logger.addHandler(ch)

        return logger

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Загрузка конфигурации"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _generate_session_id(self) -> str:
        """Генерация ID сессии"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    async def process_input(self, user_input: str, mode: str = "text") -> str:
        """
        Обработка пользовательского ввода

        Args:
            user_input: Текст или путь к аудио
            mode: "text" или "voice"
        """
        try:
            # 1. Преобразование голоса в текст (если нужно)
            if mode == "voice":
                user_input = await self.voice.transcribe(user_input)
                self.console.print(f"[blue]Вы:[/blue] {user_input}")

            # 2. Сохранение в историю
            self.context.conversation_history.append({
                "role": "user",
                "content": user_input,
                "timestamp": datetime.now().isoformat()
            })

            # 3. Поиск релевантного контекста в RAG
            relevant_context = await self.rag.search(user_input, top_k=5)

            # 4. Определение необходимых инструментов
            tools_needed = await self._analyze_tools_needed(user_input)

            # 5. Подготовка системного промпта
            system_prompt = self._build_system_prompt(relevant_context, tools_needed)

            # 6. Получение ответа от Claude с использованием MCP tools
            response = await self._get_claude_response(
                user_input,
                system_prompt,
                tools_needed
            )

            # 7. Сохранение ответа в историю и память
            self.context.conversation_history.append({
                "role": "assistant",
                "content": response,
                "timestamp": datetime.now().isoformat()
            })

            # 8. Обновление долгосрочной памяти
            await self.memory.save_interaction(user_input, response)

            # 9. Сохранение в RAG для будущего контекста
            await self.rag.add_document(
                f"Q: {user_input}\nA: {response}",
                metadata={
                    "type": "conversation",
                    "timestamp": datetime.now().isoformat()
                }
            )

            return response

        except Exception as e:
            self.logger.error(f"Error processing input: {e}")
            return f"Извините, произошла ошибка: {str(e)}"

    async def _analyze_tools_needed(self, user_input: str) -> List[str]:
        """Анализ какие инструменты нужны для запроса"""
        tools = []

        # Простая эвристика для определения нужных инструментов
        input_lower = user_input.lower()

        if any(word in input_lower for word in ["файл", "файлы", "документ", "папка"]):
            tools.append("filesystem")

        if any(word in input_lower for word in ["найди", "поиск", "погугли", "search"]):
            tools.append("web_search")

        if any(word in input_lower for word in ["календарь", "встреча", "событие"]):
            tools.append("calendar")

        if any(word in input_lower for word in ["github", "репозиторий", "код", "pr"]):
            tools.append("github")

        return tools

    def _build_system_prompt(
        self,
        relevant_context: List[Dict[str, Any]],
        tools: List[str]
    ) -> str:
        """Построение системного промпта"""

        context_text = ""
        if relevant_context:
            context_text = "\n\n# Релевантный контекст из памяти:\n"
            for i, ctx in enumerate(relevant_context, 1):
                context_text += f"\n{i}. {ctx['content']}\n"

        tools_text = ""
        if tools:
            tools_text = f"\n\n# Доступные инструменты: {', '.join(tools)}"

        prompt = f"""Ты - God Agent, персональный AI-ассистент Олега.

# О пользователе:
- Имя: Олег
- Профессия: Flutter разработчик, 4+ года опыта
- Интересы: ML, стартапы, технологии
- Работает удаленно, планирует свой стартап

# Твои возможности:
1. Работа с файлами и документами
2. Поиск информации в интернете
3. Управление календарем и задачами
4. Интеграция с GitHub
5. Работа с контекстом из прошлых разговоров
6. Проактивные предложения и напоминания

# Твой стиль:
- Профессиональный, но дружелюбный
- Конкретный и по делу
- Проактивный - предлагай решения
- Помогай структурировать задачи
{context_text}{tools_text}

# Текущая сессия: {self.context.session_id}
# Время: {datetime.now().strftime("%Y-%m-%d %H:%M")}

Отвечай на русском языке. Будь полезным помощником!"""

        return prompt

    async def _get_claude_response(
        self,
        user_input: str,
        system_prompt: str,
        tools_needed: List[str]
    ) -> str:
        """Получение ответа от Claude с использованием инструментов"""

        # Подготовка истории сообщений
        messages = []

        # Добавляем последние N сообщений для контекста
        recent_history = self.context.conversation_history[-10:]
        for msg in recent_history[:-1]:  # Исключаем последнее (текущее) сообщение
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        # Добавляем текущий запрос
        messages.append({
            "role": "user",
            "content": user_input
        })

        # Получение MCP tools
        mcp_tools = []
        if tools_needed:
            mcp_tools = await self.mcp.get_tools(tools_needed)

        # Вызов Claude API
        try:
            if mcp_tools:
                # С инструментами
                response = self.anthropic.messages.create(
                    model=self.config['models']['main']['model'],
                    max_tokens=self.config['models']['main']['max_tokens'],
                    temperature=self.config['models']['main']['temperature'],
                    system=system_prompt,
                    messages=messages,
                    tools=mcp_tools
                )

                # Обработка tool calls
                response_text = await self._handle_tool_calls(response)

            else:
                # Без инструментов
                response = self.anthropic.messages.create(
                    model=self.config['models']['main']['model'],
                    max_tokens=self.config['models']['main']['max_tokens'],
                    temperature=self.config['models']['main']['temperature'],
                    system=system_prompt,
                    messages=messages
                )

                response_text = response.content[0].text

            return response_text

        except Exception as e:
            self.logger.error(f"Claude API error: {e}")
            return f"Ошибка при обращении к Claude API: {str(e)}"

    async def _handle_tool_calls(self, response) -> str:
        """Обработка вызовов инструментов"""
        result_parts = []

        for content_block in response.content:
            if content_block.type == "text":
                result_parts.append(content_block.text)

            elif content_block.type == "tool_use":
                tool_name = content_block.name
                tool_input = content_block.input

                # Выполнение инструмента
                tool_result = await self.mcp.execute_tool(tool_name, tool_input)

                result_parts.append(
                    f"\n[Выполнено: {tool_name}]\n{tool_result}\n"
                )

        return "\n".join(result_parts)

    async def start_voice_mode(self):
        """Запуск режима голосового взаимодействия"""
        if not self.voice:
            self.console.print("[red]Голосовой режим отключен в конфигурации[/red]")
            return

        # self.console.print(Panel(
        #     "[bold green]God Agent - Голосовой режим[/bold green]\n"
        #     "Скажите 'агент' для активации\n"
        #     "Скажите 'выход' для завершения",
        #     title="🎤 Voice Mode"
        # ))

        while True:
            try:
                # Ожидание wake word
                if self.config['voice']['wake_word']['enabled']:
                    self.console.print("[dim]Жду команду...[/dim]")
                    await self.voice.wait_for_wake_word(
                        self.config['voice']['wake_word']['phrase']
                    )
                    self.console.print("[green]✓ Активирован! Говорите...[/green]")

                # Запись аудио
                audio_path = await self.voice.record_audio()

                if not audio_path:
                    continue

                # Обработка запроса
                response = await self.process_input(audio_path, mode="voice")

                # Вывод ответа
                self.console.print(Panel(
                    Markdown(response),
                    title="[bold blue]God Agent[/bold blue]",
                    border_style="blue"
                ))

                # Озвучка ответа (опционально)
                if self.config['voice']['output']['enabled']:
                    await self.voice.speak(response)

                # Проверка на выход
                if "выход" in response.lower() or "exit" in response.lower():
                    break

            except KeyboardInterrupt:
                break
            except Exception as e:
                self.logger.error(f"Voice mode error: {e}")
                self.console.print(f"[red]Ошибка: {e}[/red]")

        self.console.print("[yellow]Голосовой режим завершен[/yellow]")

    async def start_text_mode(self):
        """Запуск режима текстового взаимодействия"""
        self.console.print(Panel(
            "[bold green]God Agent - Текстовый режим[/bold green]\n"
            "Введите 'exit' для выхода\n"
            "Введите '/help' для справки",
            title="💬 Text Mode"
        ))

        while True:
            try:
                # Получение ввода
                user_input = self.console.input("[bold blue]Вы:[/bold blue] ")

                if not user_input.strip():
                    continue

                # Команды
                if user_input.lower() == "exit":
                    break

                if user_input.lower() == "/help":
                    self._show_help()
                    continue

                if user_input.lower() == "/stats":
                    await self._show_stats()
                    continue

                if user_input.lower() == "/clear":
                    self.context.conversation_history.clear()
                    self.console.print("[green]История очищена[/green]")
                    continue

                # Обработка запроса
                response = await self.process_input(user_input, mode="text")

                # Вывод ответа
                self.console.print(Panel(
                    Markdown(response),
                    title="[bold green]God Agent[/bold green]",
                    border_style="green"
                ))

            except KeyboardInterrupt:
                break
            except Exception as e:
                self.logger.error(f"Text mode error: {e}")
                self.console.print(f"[red]Ошибка: {e}[/red]")

        self.console.print("[yellow]Текстовый режим завершен[/yellow]")

    def _show_help(self):
        """Показать справку"""
        help_text = """
# Доступные команды:

- `/help` - показать эту справку
- `/stats` - показать статистику
- `/clear` - очистить историю разговора
- `exit` - выйти из режима

# Возможности God Agent:

1. **Работа с файлами** - создание, чтение, поиск файлов
2. **Веб-поиск** - поиск актуальной информации
3. **GitHub** - работа с репозиториями, PR, issues
4. **Календарь** - управление встречами и событиями
5. **RAG** - контекст из прошлых разговоров
6. **Задачи** - отслеживание и планирование

# Примеры запросов:

- "Найди все файлы с TODO в моем проекте"
- "Что нового в Flutter 3.19?"
- "Создай задачу на завтра: код-ревью PR"
- "Расскажи что мы обсуждали про ML вчера"
"""
        self.console.print(Panel(Markdown(help_text), title="📖 Справка"))

    async def _show_stats(self):
        """Показать статистику"""
        stats = await self.memory.get_stats()

        stats_text = f"""
# Статистика God Agent

**Текущая сессия:** {self.context.session_id}
**Сообщений в истории:** {len(self.context.conversation_history)}
**Документов в RAG:** {await self.rag.get_document_count()}
**Активных задач:** {len(self.tasks.get_active_tasks())}

**База знаний:**
- Всего взаимодействий: {stats.get('total_interactions', 0)}
- Последнее обновление: {stats.get('last_update', 'N/A')}
"""
        self.console.print(Panel(Markdown(stats_text), title="📊 Статистика"))

    async def shutdown(self):
        """Корректное завершение работы"""
        self.logger.info("Shutting down God Agent...")

        # Сохранение состояния
        await self.memory.save_session(self.context)

        # Закрытие соединений
        await self.mcp.close()
        await self.rag.close()

        self.console.print("[green]God Agent завершил работу[/green]")


async def main():
    """Точка входа"""
    agent = GodAgent()

    try:
        # Выбор режима
        console = Console()
        console.print(Panel(
            "[bold]Выберите режим работы:[/bold]\n"
            "1. Текстовый режим\n"
            "2. Голосовой режим\n"
            "3. Смешанный режим",
            title="God Agent"
        ))

        mode = console.input("[blue]Режим (1/2/3):[/blue] ").strip()

        if mode == "1":
            await agent.start_text_mode()
        elif mode == "2":
            await agent.start_voice_mode()
        elif mode == "3":
            # TODO: Реализовать смешанный режим
            console.print("[yellow]Смешанный режим в разработке[/yellow]")
            await agent.start_text_mode()
        else:
            console.print("[red]Неверный выбор[/red]")

    finally:
        await agent.shutdown()


if __name__ == "__main__":
    asyncio.run(main())