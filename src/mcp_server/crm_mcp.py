"""
MCP Server для CRM интеграции
Управление пользователями и тикетами
"""
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Support CRM Server")

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

class TicketCreate(BaseModel):
    user_id: str
    subject: str
    description: str
    category: str
    priority: Optional[str] = "medium"

class TicketUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    resolution: Optional[str] = None

# ============================================================================
# CRM система
# ============================================================================

class CRM:
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.users_file = self.data_dir / "users.json"
        self.tickets_file = self.data_dir / "tickets.json"
        self.users = {}
        self.tickets = {}
        self.load_data()
    
    def load_data(self):
        """Загружает данные из JSON файлов"""
        try:
            if self.users_file.exists():
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.users = data.get('users', {})
                print(f"✓ Загружено {len(self.users)} пользователей")
            
            if self.tickets_file.exists():
                with open(self.tickets_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.tickets = data.get('tickets', {})
                print(f"✓ Загружено {len(self.tickets)} тикетов")
        except Exception as e:
            print(f"Ошибка загрузки данных: {e}")
    
    def save_data(self):
        """Сохраняет данные в JSON файлы"""
        try:
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump({"users": self.users}, f, indent=2, ensure_ascii=False)
            
            with open(self.tickets_file, 'w', encoding='utf-8') as f:
                json.dump({"tickets": self.tickets}, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Ошибка сохранения данных: {e}")
    
    def get_user(self, user_id: str) -> Optional[Dict]:
        """Получает информацию о пользователе"""
        return self.users.get(user_id)
    
    def get_user_tickets(self, user_id: str, status: Optional[str] = None) -> List[Dict]:
        """Получает тикеты пользователя"""
        tickets = []
        for ticket_id, ticket in self.tickets.items():
            if ticket['user_id'] == user_id:
                if status is None or ticket['status'] == status:
                    tickets.append(ticket)
        return tickets
    
    def get_ticket(self, ticket_id: str) -> Optional[Dict]:
        """Получает тикет по ID"""
        return self.tickets.get(ticket_id)
    
    def create_ticket(self, ticket_data: Dict) -> str:
        """Создает новый тикет"""
        # Генерируем ID
        ticket_num = len(self.tickets) + 101
        ticket_id = f"ticket_{ticket_num}"
        
        # Создаем тикет
        now = datetime.utcnow().isoformat() + 'Z'
        ticket = {
            "id": ticket_id,
            "user_id": ticket_data['user_id'],
            "subject": ticket_data['subject'],
            "description": ticket_data['description'],
            "status": "open",
            "priority": ticket_data.get('priority', 'medium'),
            "category": ticket_data['category'],
            "created": now,
            "updated": now,
            "assigned_to": "support_team",
            "tags": [],
            "history": [
                {
                    "timestamp": now,
                    "action": "created",
                    "by": ticket_data['user_id']
                }
            ]
        }
        
        self.tickets[ticket_id] = ticket
        self.save_data()
        
        return ticket_id
    
    def update_ticket(self, ticket_id: str, updates: Dict) -> bool:
        """Обновляет тикет"""
        if ticket_id not in self.tickets:
            return False
        
        ticket = self.tickets[ticket_id]
        now = datetime.utcnow().isoformat() + 'Z'
        
        # Обновляем поля
        for key, value in updates.items():
            if value is not None:
                old_value = ticket.get(key)
                ticket[key] = value
                
                # Добавляем в историю
                ticket['history'].append({
                    "timestamp": now,
                    "action": f"updated_{key}",
                    "by": "support_assistant",
                    "details": f"Changed from '{old_value}' to '{value}'"
                })
        
        ticket['updated'] = now
        
        # Если тикет решен - добавляем время решения
        if updates.get('status') == 'resolved':
            ticket['resolved'] = now
        
        self.save_data()
        return True
    
    def search_tickets(self, query: str) -> List[Dict]:
        """Поиск тикетов по ключевым словам"""
        results = []
        query_lower = query.lower()
        
        for ticket_id, ticket in self.tickets.items():
            if (query_lower in ticket['subject'].lower() or
                query_lower in ticket['description'].lower() or
                query_lower in ticket.get('category', '').lower()):
                results.append(ticket)
        
        return results

# ============================================================================
# Глобальная инстанция CRM
# ============================================================================

# Путь к данным относительно mcp_server/
DATA_DIR = Path(__file__).parent.parent / "crm_data"
crm = CRM(str(DATA_DIR))

# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/health")
async def health():
    """Проверка здоровья сервиса"""
    return {
        "status": "ok",
        "service": "Support CRM Server",
        "users": len(crm.users),
        "tickets": len(crm.tickets)
    }

@app.get("/crm/user/{user_id}")
async def get_user(user_id: str):
    """Получить информацию о пользователе"""
    user = crm.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"Пользователь {user_id} не найден")
    return user

@app.get("/crm/user/{user_id}/tickets")
async def get_user_tickets(user_id: str, status: Optional[str] = None):
    """Получить тикеты пользователя"""
    user = crm.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"Пользователь {user_id} не найден")
    
    tickets = crm.get_user_tickets(user_id, status)
    return {
        "user_id": user_id,
        "tickets": tickets,
        "total": len(tickets)
    }

@app.get("/crm/ticket/{ticket_id}")
async def get_ticket(ticket_id: str):
    """Получить тикет по ID"""
    ticket = crm.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Тикет {ticket_id} не найден")
    
    # Добавляем информацию о пользователе
    user = crm.get_user(ticket['user_id'])
    
    return {
        "ticket": ticket,
        "user": {
            "email": user.get('email'),
            "name": user.get('name'),
            "plan": user.get('plan')
        } if user else None
    }

@app.post("/crm/ticket")
async def create_ticket(ticket_data: TicketCreate):
    """Создать новый тикет"""
    # Проверяем существование пользователя
    user = crm.get_user(ticket_data.user_id)
    if not user:
        raise HTTPException(
            status_code=404, 
            detail=f"Пользователь {ticket_data.user_id} не найден"
        )
    
    ticket_id = crm.create_ticket(ticket_data.dict())
    ticket = crm.get_ticket(ticket_id)
    
    return {
        "message": "Тикет создан",
        "ticket_id": ticket_id,
        "ticket": ticket
    }

@app.put("/crm/ticket/{ticket_id}")
async def update_ticket(ticket_id: str, updates: TicketUpdate):
    """Обновить тикет"""
    success = crm.update_ticket(ticket_id, updates.dict(exclude_none=True))
    
    if not success:
        raise HTTPException(status_code=404, detail=f"Тикет {ticket_id} не найден")
    
    ticket = crm.get_ticket(ticket_id)
    return {
        "message": "Тикет обновлен",
        "ticket": ticket
    }

@app.get("/crm/tickets/search")
async def search_tickets(q: str):
    """Поиск тикетов"""
    results = crm.search_tickets(q)
    return {
        "query": q,
        "results": results,
        "total": len(results)
    }

@app.get("/crm/stats")
async def get_stats():
    """Статистика CRM"""
    open_tickets = len([t for t in crm.tickets.values() if t['status'] == 'open'])
    in_progress = len([t for t in crm.tickets.values() if t['status'] == 'in_progress'])
    resolved = len([t for t in crm.tickets.values() if t['status'] == 'resolved'])
    
    # Статистика по планам
    plans = {}
    for user in crm.users.values():
        plan = user.get('plan', 'unknown')
        plans[plan] = plans.get(plan, 0) + 1
    
    return {
        "users": {
            "total": len(crm.users),
            "by_plan": plans
        },
        "tickets": {
            "total": len(crm.tickets),
            "open": open_tickets,
            "in_progress": in_progress,
            "resolved": resolved
        }
    }

# ============================================================================
# Запуск
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("🚀 Support CRM Server")
    print("=" * 60)
    print(f"📁 Данные: {DATA_DIR}")
    
    uvicorn.run(app, host="0.0.0.0", port=8001)
