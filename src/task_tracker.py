"""
Task Tracker для God Agent
Управление задачами и напоминаниями
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class TaskStatus(Enum):
    """Статусы задач"""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Приоритеты задач"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Task:
    """Задача"""
    id: str
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    created_at: str
    due_date: Optional[str] = None
    completed_at: Optional[str] = None
    tags: List[str] = None
    subtasks: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.subtasks is None:
            self.subtasks = []


class TaskTracker:
    """Менеджер задач"""
    
    def __init__(self, storage_path: str = "./data/tasks.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.tasks: Dict[str, Task] = {}
        self._load_tasks()
        
        print(f"✅ Task Tracker инициализирован: {len(self.tasks)} задач")
    
    def _load_tasks(self):
        """Загрузка задач из файла"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for task_id, task_data in data.items():
                    # Преобразование enum из строк
                    task_data['status'] = TaskStatus(task_data['status'])
                    task_data['priority'] = TaskPriority(task_data['priority'])
                    
                    self.tasks[task_id] = Task(**task_data)
            
            except Exception as e:
                print(f"Ошибка загрузки задач: {e}")
    
    def _save_tasks(self):
        """Сохранение задач в файл"""
        try:
            data = {}
            for task_id, task in self.tasks.items():
                task_dict = asdict(task)
                # Преобразование enum в строки
                task_dict['status'] = task.status.value
                task_dict['priority'] = task.priority.value
                data[task_id] = task_dict
            
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        except Exception as e:
            print(f"Ошибка сохранения задач: {e}")
    
    def _generate_task_id(self) -> str:
        """Генерация уникального ID задачи"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"task_{timestamp}_{len(self.tasks)}"
    
    def create_task(
        self,
        title: str,
        description: str = "",
        priority: TaskPriority = TaskPriority.MEDIUM,
        due_date: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Task:
        """
        Создание новой задачи
        
        Args:
            title: Название задачи
            description: Описание
            priority: Приоритет
            due_date: Срок выполнения (ISO формат)
            tags: Теги
        
        Returns:
            Созданная задача
        """
        task_id = self._generate_task_id()
        
        task = Task(
            id=task_id,
            title=title,
            description=description,
            status=TaskStatus.TODO,
            priority=priority,
            created_at=datetime.now().isoformat(),
            due_date=due_date,
            tags=tags or []
        )
        
        self.tasks[task_id] = task
        self._save_tasks()
        
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Получение задачи по ID"""
        return self.tasks.get(task_id)
    
    def update_task(
        self,
        task_id: str,
        **kwargs
    ) -> Optional[Task]:
        """
        Обновление задачи
        
        Args:
            task_id: ID задачи
            **kwargs: Поля для обновления
        
        Returns:
            Обновленная задача или None
        """
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        # Обновление полей
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        
        self._save_tasks()
        return task
    
    def complete_task(self, task_id: str) -> Optional[Task]:
        """
        Завершение задачи
        
        Args:
            task_id: ID задачи
        
        Returns:
            Завершенная задача или None
        """
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        task.status = TaskStatus.DONE
        task.completed_at = datetime.now().isoformat()
        
        self._save_tasks()
        return task
    
    def delete_task(self, task_id: str) -> bool:
        """
        Удаление задачи
        
        Args:
            task_id: ID задачи
        
        Returns:
            True если удалена, False если не найдена
        """
        if task_id in self.tasks:
            del self.tasks[task_id]
            self._save_tasks()
            return True
        return False
    
    def get_all_tasks(self) -> List[Task]:
        """Получение всех задач"""
        return list(self.tasks.values())
    
    def get_active_tasks(self) -> List[Task]:
        """Получение активных задач (TODO и IN_PROGRESS)"""
        return [
            task for task in self.tasks.values()
            if task.status in [TaskStatus.TODO, TaskStatus.IN_PROGRESS]
        ]
    
    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """Получение задач по статусу"""
        return [
            task for task in self.tasks.values()
            if task.status == status
        ]
    
    def get_tasks_by_priority(self, priority: TaskPriority) -> List[Task]:
        """Получение задач по приоритету"""
        return [
            task for task in self.tasks.values()
            if task.priority == priority
        ]
    
    def get_tasks_by_tag(self, tag: str) -> List[Task]:
        """Получение задач по тегу"""
        return [
            task for task in self.tasks.values()
            if tag in task.tags
        ]
    
    def get_overdue_tasks(self) -> List[Task]:
        """Получение просроченных задач"""
        now = datetime.now()
        overdue = []
        
        for task in self.tasks.values():
            if task.status != TaskStatus.DONE and task.due_date:
                try:
                    due_date = datetime.fromisoformat(task.due_date)
                    if due_date < now:
                        overdue.append(task)
                except:
                    pass
        
        return overdue
    
    def get_upcoming_tasks(self, days: int = 7) -> List[Task]:
        """
        Получение задач на ближайшие дни
        
        Args:
            days: Количество дней вперед
        
        Returns:
            Список задач
        """
        now = datetime.now()
        future = now + timedelta(days=days)
        upcoming = []
        
        for task in self.tasks.values():
            if task.status != TaskStatus.DONE and task.due_date:
                try:
                    due_date = datetime.fromisoformat(task.due_date)
                    if now <= due_date <= future:
                        upcoming.append(task)
                except:
                    pass
        
        return sorted(upcoming, key=lambda t: t.due_date or "")
    
    def search_tasks(self, query: str) -> List[Task]:
        """
        Поиск задач по тексту
        
        Args:
            query: Поисковый запрос
        
        Returns:
            Список найденных задач
        """
        query_lower = query.lower()
        results = []
        
        for task in self.tasks.values():
            if (query_lower in task.title.lower() or
                query_lower in task.description.lower() or
                any(query_lower in tag.lower() for tag in task.tags)):
                results.append(task)
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получение статистики по задачам"""
        all_tasks = self.get_all_tasks()
        
        return {
            "total": len(all_tasks),
            "todo": len(self.get_tasks_by_status(TaskStatus.TODO)),
            "in_progress": len(self.get_tasks_by_status(TaskStatus.IN_PROGRESS)),
            "done": len(self.get_tasks_by_status(TaskStatus.DONE)),
            "cancelled": len(self.get_tasks_by_status(TaskStatus.CANCELLED)),
            "overdue": len(self.get_overdue_tasks()),
            "upcoming": len(self.get_upcoming_tasks()),
            "by_priority": {
                "urgent": len(self.get_tasks_by_priority(TaskPriority.URGENT)),
                "high": len(self.get_tasks_by_priority(TaskPriority.HIGH)),
                "medium": len(self.get_tasks_by_priority(TaskPriority.MEDIUM)),
                "low": len(self.get_tasks_by_priority(TaskPriority.LOW)),
            }
        }
    
    def format_task(self, task: Task, detailed: bool = False) -> str:
        """
        Форматирование задачи для вывода
        
        Args:
            task: Задача
            detailed: Показывать подробности
        
        Returns:
            Отформатированная строка
        """
        status_emoji = {
            TaskStatus.TODO: "⭕",
            TaskStatus.IN_PROGRESS: "🔄",
            TaskStatus.DONE: "✅",
            TaskStatus.CANCELLED: "❌"
        }
        
        priority_emoji = {
            TaskPriority.LOW: "🔵",
            TaskPriority.MEDIUM: "🟡",
            TaskPriority.HIGH: "🟠",
            TaskPriority.URGENT: "🔴"
        }
        
        parts = [
            f"{status_emoji[task.status]} {priority_emoji[task.priority]}",
            f"**{task.title}**"
        ]
        
        if task.due_date:
            parts.append(f"(до {task.due_date[:10]})")
        
        if detailed:
            details = [f"\n  ID: {task.id}"]
            
            if task.description:
                details.append(f"  Описание: {task.description}")
            
            if task.tags:
                details.append(f"  Теги: {', '.join(task.tags)}")
            
            details.append(f"  Создано: {task.created_at[:10]}")
            
            if task.completed_at:
                details.append(f"  Завершено: {task.completed_at[:10]}")
            
            parts.append("".join(details))
        
        return " ".join(parts)
    
    def format_task_list(
        self,
        tasks: List[Task],
        detailed: bool = False
    ) -> str:
        """
        Форматирование списка задач
        
        Args:
            tasks: Список задач
            detailed: Показывать подробности
        
        Returns:
            Отформатированная строка
        """
        if not tasks:
            return "Нет задач"
        
        lines = []
        for i, task in enumerate(tasks, 1):
            lines.append(f"{i}. {self.format_task(task, detailed)}")
        
        return "\n".join(lines)
