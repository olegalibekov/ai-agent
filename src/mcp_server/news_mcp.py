"""
News MCP Server
Управление постами, история, аналитика
"""
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="News MCP Server")

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

class NewsPost(BaseModel):
    title: str
    description: str
    url: str
    source: str
    published_at: Optional[str] = None

class PostUpdate(BaseModel):
    telegram_message_id: Optional[int] = None
    views: Optional[int] = None
    clicks: Optional[int] = None
    reactions: Optional[Dict] = None

# ============================================================================
# Data Manager
# ============================================================================

class PostsManager:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.posts_file = self.data_dir / "posts_history.json"
        self.settings_file = self.data_dir / "settings.json"
        
        self.posts = []
        self.settings = {}
        
        self.load_data()
    
    def load_data(self):
        """Загружает данные"""
        # Posts
        if self.posts_file.exists():
            with open(self.posts_file, 'r', encoding='utf-8') as f:
                self.posts = json.load(f)
        
        # Settings
        if self.settings_file.exists():
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                self.settings = json.load(f)
        else:
            # Дефолтные настройки
            self.settings = {
                "max_posts_per_day": 10,
                "min_interval_minutes": 60,
                "categories": ["tech", "business", "science", "world"],
                "sources": ["TechCrunch", "Hacker News", "Reuters"],
                "enabled": True
            }
            self.save_settings()
        
        print(f"✓ Загружено {len(self.posts)} постов")
    
    def save_posts(self):
        """Сохраняет посты"""
        with open(self.posts_file, 'w', encoding='utf-8') as f:
            json.dump(self.posts, f, ensure_ascii=False, indent=2)
    
    def save_settings(self):
        """Сохраняет настройки"""
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=2)
    
    def add_post(self, post_data: Dict) -> str:
        """Добавляет пост"""
        post_id = f"post_{len(self.posts) + 1}"
        
        post = {
            "id": post_id,
            "title": post_data['title'],
            "description": post_data.get('description', ''),
            "url": post_data['url'],
            "source": post_data['source'],
            "published_at": post_data.get('published_at'),
            "posted_at": datetime.utcnow().isoformat(),
            "telegram_message_id": None,
            "views": 0,
            "clicks": 0,
            "reactions": {}
        }
        
        self.posts.append(post)
        self.save_posts()
        
        return post_id
    
    def get_post(self, post_id: str) -> Optional[Dict]:
        """Получает пост по ID"""
        return next((p for p in self.posts if p['id'] == post_id), None)
    
    def update_post(self, post_id: str, updates: Dict) -> bool:
        """Обновляет пост"""
        post = self.get_post(post_id)
        if not post:
            return False
        
        for key, value in updates.items():
            if value is not None:
                post[key] = value
        
        self.save_posts()
        return True
    
    def get_recent_posts(self, hours: int = 24) -> List[Dict]:
        """Получает недавние посты"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        recent = []
        for post in self.posts:
            posted_at = datetime.fromisoformat(post['posted_at'])
            if posted_at >= cutoff:
                recent.append(post)
        
        return recent
    
    def can_post_now(self) -> Dict:
        """Проверяет можно ли постить сейчас"""
        if not self.settings.get('enabled', True):
            return {
                "can_post": False,
                "reason": "Бот отключен в настройках"
            }
        
        # Проверяем лимит постов за день
        posts_today = len(self.get_recent_posts(24))
        max_posts = self.settings.get('max_posts_per_day', 10)
        
        if posts_today >= max_posts:
            return {
                "can_post": False,
                "reason": f"Достигнут лимит {max_posts} постов в день"
            }
        
        # Проверяем минимальный интервал
        if self.posts:
            last_post = self.posts[-1]
            last_posted = datetime.fromisoformat(last_post['posted_at'])
            min_interval = timedelta(minutes=self.settings.get('min_interval_minutes', 60))
            
            time_since_last = datetime.utcnow() - last_posted
            
            if time_since_last < min_interval:
                remaining = min_interval - time_since_last
                return {
                    "can_post": False,
                    "reason": f"Нужно подождать ещё {remaining.seconds // 60} минут"
                }
        
        return {
            "can_post": True,
            "posts_today": posts_today,
            "max_posts": max_posts
        }
    
    def get_stats(self) -> Dict:
        """Возвращает статистику"""
        total = len(self.posts)
        
        if total == 0:
            return {
                "total_posts": 0,
                "today": 0,
                "week": 0,
                "total_views": 0,
                "total_clicks": 0
            }
        
        today = len(self.get_recent_posts(24))
        week = len(self.get_recent_posts(24 * 7))
        
        total_views = sum(p.get('views', 0) for p in self.posts)
        total_clicks = sum(p.get('clicks', 0) for p in self.posts)
        
        # Популярные источники
        sources = {}
        for post in self.posts:
            source = post['source']
            sources[source] = sources.get(source, 0) + 1
        
        return {
            "total_posts": total,
            "today": today,
            "week": week,
            "total_views": total_views,
            "total_clicks": total_clicks,
            "top_sources": sorted(sources.items(), key=lambda x: x[1], reverse=True)[:3]
        }

# ============================================================================
# Глобальная инстанция
# ============================================================================

manager = PostsManager()

# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/health")
async def health():
    """Проверка здоровья"""
    return {
        "status": "ok",
        "service": "News MCP Server",
        "posts": len(manager.posts)
    }

@app.get("/posts")
async def get_posts(hours: int = 24):
    """Получить недавние посты"""
    posts = manager.get_recent_posts(hours)
    return {"posts": posts, "total": len(posts)}

@app.get("/posts/{post_id}")
async def get_post(post_id: str):
    """Получить пост по ID"""
    post = manager.get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Пост не найден")
    return post

@app.post("/posts")
async def create_post(post: NewsPost):
    """Создать пост"""
    post_id = manager.add_post(post.dict())
    return {"message": "Пост создан", "post_id": post_id}

@app.put("/posts/{post_id}")
async def update_post(post_id: str, updates: PostUpdate):
    """Обновить пост"""
    success = manager.update_post(post_id, updates.dict(exclude_none=True))
    if not success:
        raise HTTPException(status_code=404, detail="Пост не найден")
    return {"message": "Пост обновлён"}

@app.get("/can-post")
async def can_post():
    """Проверить можно ли постить"""
    return manager.can_post_now()

@app.get("/settings")
async def get_settings():
    """Получить настройки"""
    return manager.settings

@app.put("/settings")
async def update_settings(settings: Dict):
    """Обновить настройки"""
    manager.settings.update(settings)
    manager.save_settings()
    return {"message": "Настройки обновлены"}

@app.get("/stats")
async def get_stats():
    """Получить статистику"""
    return manager.get_stats()

# ============================================================================
# Запуск
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("🚀 News MCP Server")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8002)
