#!/usr/bin/env python3
"""
Team Assistant CLI
Интеллектуальный помощник команды
"""
import argparse
import requests
import json
from typing import List, Dict, Optional

BACKEND_URL = "http://localhost:8000"
MCP_URL = "http://localhost:8001"

class TeamAssistant:
    def __init__(self):
        self.backend_url = BACKEND_URL
        self.mcp_url = MCP_URL
    
    # ========================================================================
    # Индексация
    # ========================================================================
    
    def index(self, kb_path: str):
        """Индексирует базу знаний"""
        print(f"📚 Индексирую базу знаний: {kb_path}\n")
        
        try:
            resp = requests.post(
                f"{self.backend_url}/index",
                json={"kb_path": kb_path},
                timeout=180
            )
            
            if resp.status_code == 200:
                result = resp.json()
                print(f"✓ {result['message']}")
                print(f"\n📊 Статистика:")
                print(f"  Всего чанков: {result['total_chunks']}")
                print(f"\n📂 Типы документов:")
                for doc_type, count in result['types'].items():
                    print(f"  {doc_type}: {count}")
            else:
                print(f"✗ Ошибка: {resp.text}")
        except Exception as e:
            print(f"✗ Ошибка: {e}")
    
    # ========================================================================
    # Статус проекта
    # ========================================================================
    
    def status(self):
        """Показывает статус проекта"""
        print("📊 Загружаю статус проекта...\n")
        
        try:
            resp = requests.get(f"{self.mcp_url}/project/status")
            
            if resp.status_code == 200:
                data = resp.json()
                
                sprint = data['sprint']['sprint']
                stats = data['sprint']
                
                print("="*60)
                print(f"📊 СТАТУС ПРОЕКТА: CloudDocs v2.0")
                print("="*60)
                
                # Спринт
                print(f"\n🎯 {sprint['name']}")
                print(f"   Период: {sprint['start_date']} - {sprint['end_date']}")
                print(f"   Прогресс: {stats['completed']}/{stats['total_tasks']} задач ({stats['completion_percent']}%)")
                
                if sprint.get('release_planned'):
                    print(f"   🚀 Релиз: {sprint['release_date']}")
                
                # Блокеры
                if data['blockers']['blocked_tasks'] > 0 or data['blockers']['release_blockers'] > 0:
                    print(f"\n⚠️  Блокеры:")
                    if data['blockers']['blocked_tasks'] > 0:
                        print(f"   Заблокированных задач: {data['blockers']['blocked_tasks']}")
                    if data['blockers']['release_blockers'] > 0:
                        print(f"   Блокируют релиз: {data['blockers']['release_blockers']}")
                
                # High priority
                if data['high_priority_open'] > 0:
                    print(f"\n🔥 Критические задачи: {data['high_priority_open']}")
                
                # Команда
                print(f"\n👥 Команда:")
                for member_data in data['team']:
                    member = member_data['member']
                    emoji = member.get('avatar', '👤')
                    print(f"   {emoji} {member['name']}: {member_data['task_count']} задач ({member_data['load_percent']}% загрузки)")
            else:
                print(f"✗ Ошибка: {resp.text}")
        except Exception as e:
            print(f"✗ Ошибка: {e}")
    
    # ========================================================================
    # Управление задачами
    # ========================================================================
    
    def tasks(self, status: Optional[str] = None, priority: Optional[str] = None,
              assignee: Optional[str] = None):
        """Показывает задачи с фильтрами"""
        print("📋 Загружаю задачи...\n")
        
        try:
            params = {}
            if status:
                params['status'] = status
            if priority:
                params['priority'] = priority
            if assignee:
                params['assignee'] = assignee
            
            resp = requests.get(f"{self.mcp_url}/tasks", params=params)
            
            if resp.status_code == 200:
                data = resp.json()
                tasks = data['tasks']
                
                if not tasks:
                    print("Задач не найдено")
                    return
                
                print(f"Найдено задач: {len(tasks)}\n")
                
                # Группируем по приоритету
                by_priority = {'high': [], 'medium': [], 'low': []}
                for task in tasks:
                    by_priority[task['priority']].append(task)
                
                for priority_level in ['high', 'medium', 'low']:
                    priority_tasks = by_priority[priority_level]
                    if not priority_tasks:
                        continue
                    
                    emoji = {'high': '🔥', 'medium': '⚡', 'low': '📝'}[priority_level]
                    print(f"{emoji} {priority_level.upper()} ({len(priority_tasks)}):")
                    
                    for task in priority_tasks:
                        status_emoji = {
                            'open': '🔓',
                            'in_progress': '⏳',
                            'blocked': '🚫',
                            'waiting_review': '👀',
                            'done': '✅'
                        }.get(task['status'], '📋')
                        
                        assignee = task.get('assignee', 'неназначена')
                        print(f"  {status_emoji} {task['id']}: {task['title']}")
                        print(f"     Статус: {task['status']}, Назначена: {assignee}")
                    print()
            else:
                print(f"✗ Ошибка: {resp.text}")
        except Exception as e:
            print(f"✗ Ошибка: {e}")
    
    def task_create(self, title: str, priority: str = "medium", 
                   assignee: Optional[str] = None, estimate: Optional[int] = None):
        """Создает задачу"""
        print(f"📝 Создаю задачу: {title}\n")
        
        try:
            task_data = {
                "title": title,
                "description": f"Создано через Team Assistant CLI",
                "priority": priority,
                "assignee": assignee,
                "estimate_hours": estimate,
                "labels": []
            }
            
            resp = requests.post(f"{self.mcp_url}/tasks", json=task_data)
            
            if resp.status_code == 200:
                result = resp.json()
                task = result['task']
                
                print(f"✅ Задача создана: {task['id']}")
                print(f"\n📋 Детали:")
                print(f"   Название: {task['title']}")
                print(f"   Приоритет: {task['priority']}")
                print(f"   Назначена: {task.get('assignee', 'никому')}")
                print(f"   Спринт: {task.get('sprint', 'не назначен')}")
                if estimate:
                    print(f"   Оценка: {estimate} часов")
                
                # Показываем прямой API запрос
                print(f"\n💡 API запрос:")
                print(f"   curl -X POST http://localhost:8001/tasks \\")
                print(f"     -H 'Content-Type: application/json' \\")
                print(f"     -d '{json.dumps(task_data, ensure_ascii=False)}'")
            else:
                print(f"✗ Ошибка: {resp.text}")
        except Exception as e:
            print(f"✗ Ошибка: {e}")
    
    def task_create_interactive(self):
        """Интерактивное создание задачи"""
        print("📝 СОЗДАНИЕ НОВОЙ ЗАДАЧИ\n")
        print("="*60)
        
        # Название
        title = input("📌 Название задачи: ")
        if not title:
            print("✗ Название обязательно")
            return
        
        # Описание
        description = input("📄 Описание (Enter для пропуска): ")
        if not description:
            description = f"Создано через Team Assistant"
        
        # Приоритет
        print("\n⚡ Приоритет:")
        print("  1. Low")
        print("  2. Medium (по умолчанию)")
        print("  3. High")
        priority_choice = input("Выберите (1-3): ").strip()
        priority_map = {'1': 'low', '2': 'medium', '3': 'high'}
        priority = priority_map.get(priority_choice, 'medium')
        
        # Исполнитель
        print("\n👤 Исполнитель:")
        print("  1. john_doe (John Doe - Backend Lead)")
        print("  2. jane_smith (Jane Smith - Frontend)")
        print("  3. bob_wilson (Bob Wilson - DevOps)")
        print("  4. alice_brown (Alice Brown - QA)")
        print("  5. charlie_davis (Charlie Davis - PM)")
        print("  0. Не назначать")
        assignee_choice = input("Выберите (0-5): ").strip()
        assignee_map = {
            '1': 'john_doe',
            '2': 'jane_smith', 
            '3': 'bob_wilson',
            '4': 'alice_brown',
            '5': 'charlie_davis'
        }
        assignee = assignee_map.get(assignee_choice)
        
        # Оценка
        estimate_input = input("\n⏱️  Оценка в часах (Enter для пропуска): ").strip()
        estimate = int(estimate_input) if estimate_input.isdigit() else None
        
        # Метки
        labels_input = input("\n🏷️  Метки через запятую (Enter для пропуска): ").strip()
        labels = [l.strip() for l in labels_input.split(',')] if labels_input else []
        
        # Подтверждение
        print("\n" + "="*60)
        print("📋 PREVIEW:")
        print(f"   Название: {title}")
        print(f"   Описание: {description}")
        print(f"   Приоритет: {priority}")
        print(f"   Назначена: {assignee or 'никому'}")
        if estimate:
            print(f"   Оценка: {estimate} часов")
        if labels:
            print(f"   Метки: {', '.join(labels)}")
        print("="*60)
        
        confirm = input("\n✅ Создать задачу? (y/n): ")
        if confirm.lower() != 'y':
            print("❌ Отменено")
            return
        
        # Создаём
        try:
            task_data = {
                "title": title,
                "description": description,
                "priority": priority,
                "assignee": assignee,
                "estimate_hours": estimate,
                "labels": labels
            }
            
            resp = requests.post(f"{self.mcp_url}/tasks", json=task_data)
            
            if resp.status_code == 200:
                result = resp.json()
                task = result['task']
                
                print(f"\n✅ Задача создана: {task['id']}")
                print(f"\n📊 Детали:")
                print(f"   ID: {task['id']}")
                print(f"   Спринт: {task.get('sprint', 'не назначен')}")
                print(f"   Статус: {task['status']}")
            else:
                print(f"\n✗ Ошибка: {resp.text}")
        except Exception as e:
            print(f"\n✗ Ошибка: {e}")
    
    def task_update(self, task_id: str, status: Optional[str] = None,
                   assignee: Optional[str] = None, priority: Optional[str] = None):
        """Обновляет задачу"""
        print(f"🔄 Обновляю задачу {task_id}...\n")
        
        try:
            updates = {}
            if status:
                updates['status'] = status
            if assignee:
                updates['assignee'] = assignee
            if priority:
                updates['priority'] = priority
            
            resp = requests.put(f"{self.mcp_url}/tasks/{task_id}", json=updates)
            
            if resp.status_code == 200:
                result = resp.json()
                task = result['task']
                
                print(f"✅ Задача обновлена: {task['id']}")
                print(f"\n📋 Текущее состояние:")
                print(f"   Статус: {task['status']}")
                print(f"   Приоритет: {task['priority']}")
                print(f"   Назначена: {task.get('assignee', 'никому')}")
            else:
                print(f"✗ Ошибка: {resp.text}")
        except Exception as e:
            print(f"✗ Ошибка: {e}")
