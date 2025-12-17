#!/usr/bin/env python3
"""
God Agent CLI - Command Line Interface
ИСПРАВЛЕННАЯ ВЕРСИЯ с абсолютными импортами
"""

import asyncio
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Абсолютные импорты
from god_agent import GodAgent
from task_tracker import TaskTracker, TaskStatus, TaskPriority

app = typer.Typer(help="God Agent - Ваш персональный AI-ассистент")
console = Console()


@app.command()
def start(
        mode: str = typer.Option("text", help="Режим: text, voice, или mixed"),
        config: str = typer.Option("config.yaml", help="Путь к файлу конфигурации")
):
    """Запуск God Agent"""

    async def run():
        agent = GodAgent(config)

        try:
            if mode == "text":
                await agent.start_text_mode()
            elif mode == "voice":
                await agent.start_voice_mode()
            elif mode == "mixed":
                console.print("[yellow]Смешанный режим в разработке[/yellow]")
                await agent.start_text_mode()
            else:
                console.print(f"[red]Неизвестный режим: {mode}[/red]")
                return

        finally:
            await agent.shutdown()

    asyncio.run(run())


@app.command()
def task_list(
        status: str = typer.Option(None, help="Фильтр по статусу: todo, in_progress, done"),
        priority: str = typer.Option(None, help="Фильтр по приоритету: low, medium, high, urgent")
):
    """Список задач"""
    tracker = TaskTracker()

    # Фильтрация
    tasks = tracker.get_all_tasks()

    if status:
        try:
            status_enum = TaskStatus(status.lower())
            tasks = [t for t in tasks if t.status == status_enum]
        except ValueError:
            console.print(f"[red]Неверный статус: {status}[/red]")
            return

    if priority:
        try:
            priority_enum = TaskPriority(priority.lower())
            tasks = [t for t in tasks if t.priority == priority_enum]
        except ValueError:
            console.print(f"[red]Неверный приоритет: {priority}[/red]")
            return

    # Вывод
    if not tasks:
        console.print("[yellow]Нет задач[/yellow]")
        return

    table = Table(title="Задачи")
    table.add_column("ID", style="cyan")
    table.add_column("Название")
    table.add_column("Статус")
    table.add_column("Приоритет")
    table.add_column("Срок")

    for task in tasks:
        table.add_row(
            task.id,
            task.title,
            task.status.value,
            task.priority.value,
            task.due_date[:10] if task.due_date else "-"
        )

    console.print(table)


@app.command()
def task_create(
        title: str = typer.Argument(..., help="Название задачи"),
        description: str = typer.Option("", help="Описание задачи"),
        priority: str = typer.Option("medium", help="Приоритет: low, medium, high, urgent"),
        due_date: str = typer.Option(None, help="Срок (YYYY-MM-DD)")
):
    """Создать новую задачу"""
    tracker = TaskTracker()

    try:
        priority_enum = TaskPriority(priority.lower())
    except ValueError:
        console.print(f"[red]Неверный приоритет: {priority}[/red]")
        return

    task = tracker.create_task(
        title=title,
        description=description,
        priority=priority_enum,
        due_date=due_date
    )

    console.print(Panel(
        f"[green]Задача создана![/green]\n\n"
        f"ID: {task.id}\n"
        f"Название: {task.title}\n"
        f"Приоритет: {task.priority.value}\n"
        f"Статус: {task.status.value}",
        title="✅ Успех"
    ))


@app.command()
def task_complete(task_id: str = typer.Argument(..., help="ID задачи")):
    """Завершить задачу"""
    tracker = TaskTracker()
    task = tracker.complete_task(task_id)

    if task:
        console.print(f"[green]✅ Задача '{task.title}' завершена![/green]")
    else:
        console.print(f"[red]Задача {task_id} не найдена[/red]")


@app.command()
def stats():
    """Показать статистику"""

    async def run():
        agent = GodAgent()

        # Статистика памяти
        memory_stats = await agent.memory.get_stats()

        # Статистика задач
        task_stats = agent.tasks.get_statistics()

        # Статистика RAG
        rag_stats = await agent.rag.get_stats()

        # Вывод
        console.print(Panel(
            f"**Память:**\n"
            f"- Краткосрочная: {memory_stats['short_term']} сообщений\n"
            f"- Всего взаимодействий: {memory_stats.get('total_interactions', 0)}\n"
            f"- Всего сессий: {memory_stats.get('total_sessions', 0)}\n"
            f"- Фактов: {memory_stats.get('total_facts', 0)}\n\n"

            f"**Задачи:**\n"
            f"- Всего: {task_stats['total']}\n"
            f"- В работе: {task_stats['todo']} + {task_stats['in_progress']}\n"
            f"- Завершено: {task_stats['done']}\n"
            f"- Просрочено: {task_stats['overdue']}\n\n"

            f"**База знаний (RAG):**\n"
            f"- Документов: {rag_stats['total_documents']}\n"
            f"- Размер индекса: {rag_stats['index_size']}",
            title="📊 Статистика God Agent"
        ))

        await agent.shutdown()

    asyncio.run(run())


@app.command()
def export_memory(output: str = typer.Argument(..., help="Путь для сохранения")):
    """Экспорт памяти в JSON"""

    async def run():
        agent = GodAgent()
        await agent.memory.export_memory(output)
        console.print(f"[green]Память экспортирована в {output}[/green]")
        await agent.shutdown()

    asyncio.run(run())


@app.command()
def version():
    """Показать версию"""
    console.print(f"God Agent v1.0.0")


@app.command()
def info():
    """Информация о God Agent"""
    info_text = """
# God Agent - Универсальный AI-ассистент

## Возможности:
- 🎤 Голосовой ввод/вывод (Whisper + TTS)
- 🧠 RAG для работы с контекстом
- 🔧 MCP инструменты (файлы, поиск, GitHub, и т.д.)
- 💾 Долгосрочная память
- ✅ Управление задачами
- 🤖 Claude Sonnet 4 в качестве мозга

## Использование:
```bash
# Текстовый режим
python cli.py start

# Голосовой режим
python cli.py start --mode voice

# Список задач
python cli.py task-list

# Статистика
python cli.py stats
```

## Конфигурация:
Отредактируйте `config.yaml` для настройки:
- Модели AI
- MCP инструменты
- Параметры голоса
- Настройки RAG

## Документация:
https://github.com/your-repo/god-agent
"""
    console.print(Panel(info_text, title="ℹ️ God Agent"))


if __name__ == "__main__":
    app()
