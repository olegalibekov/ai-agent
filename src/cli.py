#!/usr/bin/env python3
"""
Team Assistant CLI
Интеллектуальный помощник команды разработки
"""
import sys
import argparse
from pathlib import Path

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent / 'cli_modules'))

from basic_commands import TeamAssistant
from smart_commands import SmartCommands

def main():
    parser = argparse.ArgumentParser(
        description="Team Assistant - AI помощник команды разработки",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:

  # Индексация базы знаний
  %(prog)s index knowledge_base/

  # Статус проекта
  %(prog)s status

  # Задачи с фильтрами
  %(prog)s tasks --priority high --status open
  
  # Создать задачу
  %(prog)s task create "Исправить баг" --priority high
  
  # Обновить задачу
  %(prog)s task update TASK-101 --status in_progress
  
  # AI приоритизация
  %(prog)s prioritize
  
  # Рекомендация что делать
  %(prog)s recommend
  
  # Анализ блокеров
  %(prog)s blockers
  
  # Вопрос о проекте
  %(prog)s ask "как работает авторизация?"
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Доступные команды')
    
    # ========================================================================
    # Базовые команды
    # ========================================================================
    
    # index
    index_parser = subparsers.add_parser('index', help='Индексировать базу знаний')
    index_parser.add_argument('path', help='Путь к базе знаний')
    
    # status
    status_parser = subparsers.add_parser('status', help='Статус проекта')
    
    # tasks
    tasks_parser = subparsers.add_parser('tasks', help='Показать задачи')
    tasks_parser.add_argument('--status', help='Фильтр по статусу')
    tasks_parser.add_argument('--priority', help='Фильтр по приоритету')
    tasks_parser.add_argument('--assignee', help='Фильтр по исполнителю')
    
    # task (subcommands)
    task_parser = subparsers.add_parser('task', help='Управление задачей')
    task_subparsers = task_parser.add_subparsers(dest='task_action')
    
    # task create
    create_parser = task_subparsers.add_parser('create', help='Создать задачу')
    create_parser.add_argument('title', help='Название задачи')
    create_parser.add_argument('--priority', default='medium', 
                              choices=['low', 'medium', 'high'],
                              help='Приоритет')
    create_parser.add_argument('--assignee', help='Исполнитель (ID)')
    create_parser.add_argument('--estimate', type=int, help='Оценка в часах')
    
    # task update
    update_parser = task_subparsers.add_parser('update', help='Обновить задачу')
    update_parser.add_argument('task_id', help='ID задачи')
    update_parser.add_argument('--status', help='Новый статус')
    update_parser.add_argument('--assignee', help='Новый исполнитель')
    update_parser.add_argument('--priority', help='Новый приоритет')
    
    # ========================================================================
    # Умные команды
    # ========================================================================
    
    # prioritize
    prioritize_parser = subparsers.add_parser('prioritize', 
                                             help='AI приоритизация задач')
    
    # recommend
    recommend_parser = subparsers.add_parser('recommend', 
                                            help='Рекомендация что делать')
    
    # blockers
    blockers_parser = subparsers.add_parser('blockers', 
                                           help='Анализ блокеров')
    
    # ask
    ask_parser = subparsers.add_parser('ask', help='Задать вопрос о проекте')
    ask_parser.add_argument('question', help='Ваш вопрос')
    
    # ========================================================================
    # Обработка команд
    # ========================================================================
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Инициализируем ассистентов
    basic = TeamAssistant()
    smart = SmartCommands()
    
    # Базовые команды
    if args.command == 'index':
        basic.index(args.path)
    
    elif args.command == 'status':
        basic.status()
    
    elif args.command == 'tasks':
        basic.tasks(args.status, args.priority, args.assignee)
    
    elif args.command == 'task':
        if args.task_action == 'create':
            basic.task_create(args.title, args.priority, args.assignee, args.estimate)
        elif args.task_action == 'update':
            basic.task_update(args.task_id, args.status, args.assignee, args.priority)
        else:
            task_parser.print_help()
    
    # Умные команды
    elif args.command == 'prioritize':
        smart.prioritize()
    
    elif args.command == 'recommend':
        smart.recommend_next()
    
    elif args.command == 'blockers':
        smart.analyze_blockers()
    
    elif args.command == 'ask':
        smart.ask(args.question)

if __name__ == "__main__":
    main()
