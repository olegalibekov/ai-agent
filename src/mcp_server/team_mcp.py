"""
Team MCP Server
Управление задачами, командой и проектом
"""
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Team MCP Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Модели данных
# ============================================================================

class TaskCreate(BaseModel):
    title: str
    description: str
    priority: str = "medium"
    assignee: Optional[str] = None
    estimate_hours: Optional[int] = None
    labels: List[str] = []

class TaskUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee: Optional[str] = None
    progress_percent: Optional[int] = None

# ============================================================================
# Data Manager
# ============================================================================

class ProjectData:
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.tasks = {}
        self.team = []
        self.sprints = []
        self.load_data()
    
    def load_data(self):
        """Загружает все данные"""
        # Tasks
        tasks_file = self.data_dir / "tasks.json"
        if tasks_file.exists():
            with open(tasks_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.tasks = {t['id']: t for t in data['tasks']}
        
        # Team
        team_file = self.data_dir / "team.json"
        if team_file.exists():
            with open(team_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.team = data['team']
        
        # Sprints
        sprints_file = self.data_dir / "sprints.json"
        if sprints_file.exists():
            with open(sprints_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.sprints = data['sprints']
        
        print(f"✓ Загружено: {len(self.tasks)} задач, {len(self.team)} человек, {len(self.sprints)} спринтов")
    
    def save_tasks(self):
        """Сохраняет задачи"""
        tasks_file = self.data_dir / "tasks.json"
        with open(tasks_file, 'w', encoding='utf-8') as f:
            json.dump({"tasks": list(self.tasks.values())}, f, indent=2, ensure_ascii=False)
    
    def get_tasks(self, 
                  status: Optional[str] = None,
                  priority: Optional[str] = None,
                  assignee: Optional[str] = None,
                  sprint: Optional[str] = None) -> List[Dict]:
        """Фильтрация задач"""
        tasks = list(self.tasks.values())
        
        if status:
            tasks = [t for t in tasks if t['status'] == status]
        if priority:
            tasks = [t for t in tasks if t['priority'] == priority]
        if assignee:
            tasks = [t for t in tasks if t.get('assignee') == assignee]
        if sprint:
            tasks = [t for t in tasks if t.get('sprint') == sprint]
        
        return tasks
    
    def get_blocked_tasks(self) -> List[Dict]:
        """Получает заблокированные задачи"""
        return [t for t in self.tasks.values() if t['status'] == 'blocked']
    
    def get_release_blockers(self) -> List[Dict]:
        """Получает задачи, блокирующие релиз"""
        return [t for t in self.tasks.values() if t.get('blocks_release')]
    
    def create_task(self, task_data: Dict) -> str:
        """Создает новую задачу"""
        # Генерируем ID
        task_num = len(self.tasks) + 121
        task_id = f"TASK-{task_num}"
        
        # Получаем текущий спринт
        current_sprint = next((s for s in self.sprints if s['status'] == 'active'), None)
        
        task = {
            "id": task_id,
            "title": task_data['title'],
            "description": task_data['description'],
            "status": "open",
            "priority": task_data.get('priority', 'medium'),
            "assignee": task_data.get('assignee'),
            "created": datetime.utcnow().strftime("%Y-%m-%d"),
            "updated": datetime.utcnow().strftime("%Y-%m-%d"),
            "estimate_hours": task_data.get('estimate_hours', 0),
            "sprint": current_sprint['id'] if current_sprint else None,
            "labels": task_data.get('labels', [])
        }
        
        self.tasks[task_id] = task
        self.save_tasks()
        
        return task_id
    
    def update_task(self, task_id: str, updates: Dict) -> bool:
        """Обновляет задачу"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        
        for key, value in updates.items():
            if value is not None:
                task[key] = value
        
        task['updated'] = datetime.utcnow().strftime("%Y-%m-%d")
        
        self.save_tasks()
        return True
    
    def get_team_member(self, member_id: str) -> Optional[Dict]:
        """Получает участника команды"""
        return next((m for m in self.team if m['id'] == member_id), None)
    
    def get_current_sprint(self) -> Optional[Dict]:
        """Получает текущий спринт"""
        return next((s for s in self.sprints if s['status'] == 'active'), None)
    
    def get_sprint_stats(self, sprint_id: str) -> Dict:
        """Статистика спринта"""
        sprint = next((s for s in self.sprints if s['id'] == sprint_id), None)
        if not sprint:
            return {}
        
        tasks = self.get_tasks(sprint=sprint_id)
        
        total = len(tasks)
        completed = len([t for t in tasks if t['status'] == 'done'])
        in_progress = len([t for t in tasks if t['status'] == 'in_progress'])
        blocked = len([t for t in tasks if t['status'] == 'blocked'])
        
        return {
            "sprint": sprint,
            "total_tasks": total,
            "completed": completed,
            "in_progress": in_progress,
            "blocked": blocked,
            "completion_percent": round((completed / total * 100) if total > 0 else 0, 1)
        }

# ============================================================================
# Глобальная инстанция
# ============================================================================

DATA_DIR = Path(__file__).parent.parent / "project_data"
project = ProjectData(str(DATA_DIR))

# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/health")
async def health():
    """Проверка здоровья"""
    return {
        "status": "ok",
        "service": "Team MCP Server",
        "tasks": len(project.tasks),
        "team": len(project.team),
        "sprints": len(project.sprints)
    }

@app.get("/tasks")
async def get_tasks(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assignee: Optional[str] = None,
    sprint: Optional[str] = None
):
    """Получить задачи с фильтрами"""
    tasks = project.get_tasks(status, priority, assignee, sprint)
    return {"tasks": tasks, "total": len(tasks)}

@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Получить задачу по ID"""
    task = project.tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Задача {task_id} не найдена")
    return task

@app.post("/tasks")
async def create_task(task_data: TaskCreate):
    """Создать задачу"""
    task_id = project.create_task(task_data.dict())
    task = project.tasks[task_id]
    return {"message": "Задача создана", "task_id": task_id, "task": task}

@app.put("/tasks/{task_id}")
async def update_task(task_id: str, updates: TaskUpdate):
    """Обновить задачу"""
    success = project.update_task(task_id, updates.dict(exclude_none=True))
    if not success:
        raise HTTPException(status_code=404, detail=f"Задача {task_id} не найдена")
    
    return {"message": "Задача обновлена", "task": project.tasks[task_id]}

@app.get("/tasks/blockers/all")
async def get_blockers():
    """Получить все блокеры"""
    blocked = project.get_blocked_tasks()
    release_blockers = project.get_release_blockers()
    
    return {
        "blocked_tasks": blocked,
        "release_blockers": release_blockers,
        "total_blockers": len(blocked) + len(release_blockers)
    }

@app.get("/team")
async def get_team():
    """Получить команду"""
    return {"team": project.team, "total": len(project.team)}

@app.get("/team/{member_id}")
async def get_team_member(member_id: str):
    """Получить участника команды"""
    member = project.get_team_member(member_id)
    if not member:
        raise HTTPException(status_code=404, detail=f"Участник {member_id} не найден")
    
    # Задачи участника
    tasks = project.get_tasks(assignee=member_id)
    
    return {
        "member": member,
        "tasks": tasks,
        "task_count": len(tasks)
    }

@app.get("/sprint/current")
async def get_current_sprint():
    """Получить текущий спринт"""
    sprint = project.get_current_sprint()
    if not sprint:
        raise HTTPException(status_code=404, detail="Нет активного спринта")
    
    stats = project.get_sprint_stats(sprint['id'])
    return stats

@app.get("/sprint/{sprint_id}")
async def get_sprint(sprint_id: str):
    """Получить спринт"""
    stats = project.get_sprint_stats(sprint_id)
    if not stats:
        raise HTTPException(status_code=404, detail=f"Спринт {sprint_id} не найден")
    return stats

@app.get("/project/status")
async def get_project_status():
    """Общий статус проекта"""
    sprint = project.get_current_sprint()
    
    if not sprint:
        return {"error": "Нет активного спринта"}
    
    stats = project.get_sprint_stats(sprint['id'])
    
    # Блокеры
    blocked = project.get_blocked_tasks()
    release_blockers = project.get_release_blockers()
    
    # High priority задачи
    high_tasks = project.get_tasks(priority='high', status='open')
    
    # Статус команды
    team_status = []
    for member in project.team:
        tasks = project.get_tasks(assignee=member['id'])
        team_status.append({
            "member": member,
            "task_count": len(tasks),
            "load_percent": round(member['current_load'] / member['capacity_hours_per_sprint'] * 100, 1)
        })
    
    return {
        "sprint": stats,
        "blockers": {
            "blocked_tasks": len(blocked),
            "release_blockers": len(release_blockers)
        },
        "high_priority_open": len(high_tasks),
        "team": team_status
    }

# ============================================================================
# Запуск
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("🚀 Team MCP Server")
    print("=" * 60)
    print(f"📁 Данные: {DATA_DIR}")
    
    uvicorn.run(app, host="0.0.0.0", port=8001)
