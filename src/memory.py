"""
Memory Manager для God Agent
Управление краткосрочной и долгосрочной памятью
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class Interaction:
    """Запись взаимодействия"""
    user_input: str
    agent_response: str
    timestamp: str
    session_id: str
    context: Dict[str, Any]


class MemoryManager:
    """Менеджер памяти агента"""
    
    def __init__(self, config: dict):
        self.config = config
        
        # Краткосрочная память (текущая сессия)
        self.short_term_enabled = config.get('short_term', {}).get('enabled', True)
        self.max_short_term = config.get('short_term', {}).get('max_messages', 20)
        self.short_term_memory = []
        
        # Долгосрочная память (база данных)
        self.long_term_enabled = config.get('long_term', {}).get('enabled', True)
        if self.long_term_enabled:
            db_path = config.get('long_term', {}).get('database', './data/memory.db')
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._init_database()
        
        print(f"🧠 Memory Manager инициализирован")
    
    def _init_database(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица взаимодействий
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_input TEXT NOT NULL,
                agent_response TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                session_id TEXT NOT NULL,
                context TEXT
            )
        """)
        
        # Таблица сессий
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                start_time TEXT NOT NULL,
                end_time TEXT,
                user_id TEXT,
                metadata TEXT
            )
        """)
        
        # Таблица фактов (извлеченная информация)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                source TEXT,
                timestamp TEXT NOT NULL,
                confidence REAL DEFAULT 1.0
            )
        """)
        
        # Индексы для быстрого поиска
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON interactions(timestamp)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session 
            ON interactions(session_id)
        """)
        
        conn.commit()
        conn.close()
    
    async def add_short_term(self, user_input: str, agent_response: str):
        """
        Добавление в краткосрочную память
        
        Args:
            user_input: Ввод пользователя
            agent_response: Ответ агента
        """
        if not self.short_term_enabled:
            return
        
        self.short_term_memory.append({
            "user": user_input,
            "agent": agent_response,
            "timestamp": datetime.now().isoformat()
        })
        
        # Ограничение размера
        if len(self.short_term_memory) > self.max_short_term:
            self.short_term_memory = self.short_term_memory[-self.max_short_term:]
    
    def get_short_term(self, last_n: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Получение краткосрочной памяти
        
        Args:
            last_n: Последние N записей (None = все)
        
        Returns:
            Список записей
        """
        if last_n:
            return self.short_term_memory[-last_n:]
        return self.short_term_memory
    
    async def save_interaction(
        self,
        user_input: str,
        agent_response: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Сохранение взаимодействия в долгосрочную память
        
        Args:
            user_input: Ввод пользователя
            agent_response: Ответ агента
            session_id: ID сессии
            context: Дополнительный контекст
        """
        if not self.long_term_enabled:
            return
        
        # Добавление в краткосрочную память
        await self.add_short_term(user_input, agent_response)
        
        # Сохранение в БД
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO interactions 
            (user_input, agent_response, timestamp, session_id, context)
            VALUES (?, ?, ?, ?, ?)
        """, (
            user_input,
            agent_response,
            datetime.now().isoformat(),
            session_id or "default",
            json.dumps(context or {})
        ))
        
        conn.commit()
        conn.close()
    
    async def search_interactions(
        self,
        query: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Поиск взаимодействий
        
        Args:
            query: Текст для поиска
            session_id: Фильтр по сессии
            limit: Максимум результатов
        
        Returns:
            Список найденных взаимодействий
        """
        if not self.long_term_enabled:
            return []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        sql = "SELECT * FROM interactions WHERE 1=1"
        params = []
        
        if query:
            sql += " AND (user_input LIKE ? OR agent_response LIKE ?)"
            params.extend([f"%{query}%", f"%{query}%"])
        
        if session_id:
            sql += " AND session_id = ?"
            params.append(session_id)
        
        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        conn.close()
        
        results = []
        for row in rows:
            results.append({
                "id": row[0],
                "user_input": row[1],
                "agent_response": row[2],
                "timestamp": row[3],
                "session_id": row[4],
                "context": json.loads(row[5]) if row[5] else {}
            })
        
        return results
    
    async def save_fact(
        self,
        category: str,
        content: str,
        source: Optional[str] = None,
        confidence: float = 1.0
    ):
        """
        Сохранение извлеченного факта
        
        Args:
            category: Категория факта (preferences, skills, goals, etc.)
            content: Содержание факта
            source: Источник информации
            confidence: Уверенность (0-1)
        """
        if not self.long_term_enabled:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO facts (category, content, source, timestamp, confidence)
            VALUES (?, ?, ?, ?, ?)
        """, (
            category,
            content,
            source or "conversation",
            datetime.now().isoformat(),
            confidence
        ))
        
        conn.commit()
        conn.close()
    
    async def get_facts(
        self,
        category: Optional[str] = None,
        min_confidence: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Получение фактов
        
        Args:
            category: Фильтр по категории
            min_confidence: Минимальная уверенность
        
        Returns:
            Список фактов
        """
        if not self.long_term_enabled:
            return []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        sql = "SELECT * FROM facts WHERE confidence >= ?"
        params = [min_confidence]
        
        if category:
            sql += " AND category = ?"
            params.append(category)
        
        sql += " ORDER BY timestamp DESC"
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        conn.close()
        
        return [
            {
                "id": row[0],
                "category": row[1],
                "content": row[2],
                "source": row[3],
                "timestamp": row[4],
                "confidence": row[5]
            }
            for row in rows
        ]
    
    async def save_session(self, context):
        """
        Сохранение информации о сессии
        
        Args:
            context: Контекст агента
        """
        if not self.long_term_enabled:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO sessions 
            (id, start_time, end_time, user_id, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, (
            context.session_id,
            context.timestamp.isoformat(),
            datetime.now().isoformat(),
            context.user_id,
            json.dumps(context.context_data)
        ))
        
        conn.commit()
        conn.close()
    
    async def get_stats(self) -> Dict[str, Any]:
        """Получение статистики памяти"""
        if not self.long_term_enabled:
            return {
                "short_term": len(self.short_term_memory),
                "long_term": 0
            }
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Количество взаимодействий
        cursor.execute("SELECT COUNT(*) FROM interactions")
        total_interactions = cursor.fetchone()[0]
        
        # Количество сессий
        cursor.execute("SELECT COUNT(*) FROM sessions")
        total_sessions = cursor.fetchone()[0]
        
        # Количество фактов
        cursor.execute("SELECT COUNT(*) FROM facts")
        total_facts = cursor.fetchone()[0]
        
        # Последнее обновление
        cursor.execute("SELECT MAX(timestamp) FROM interactions")
        last_update = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "short_term": len(self.short_term_memory),
            "total_interactions": total_interactions,
            "total_sessions": total_sessions,
            "total_facts": total_facts,
            "last_update": last_update
        }
    
    async def clear_short_term(self):
        """Очистка краткосрочной памяти"""
        self.short_term_memory.clear()
    
    async def export_memory(self, output_path: str):
        """
        Экспорт памяти в JSON
        
        Args:
            output_path: Путь для сохранения
        """
        if not self.long_term_enabled:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Экспорт всех данных
        data = {
            "interactions": [],
            "sessions": [],
            "facts": []
        }
        
        # Взаимодействия
        cursor.execute("SELECT * FROM interactions")
        for row in cursor.fetchall():
            data["interactions"].append({
                "id": row[0],
                "user_input": row[1],
                "agent_response": row[2],
                "timestamp": row[3],
                "session_id": row[4],
                "context": json.loads(row[5]) if row[5] else {}
            })
        
        # Сессии
        cursor.execute("SELECT * FROM sessions")
        for row in cursor.fetchall():
            data["sessions"].append({
                "id": row[0],
                "start_time": row[1],
                "end_time": row[2],
                "user_id": row[3],
                "metadata": json.loads(row[4]) if row[4] else {}
            })
        
        # Факты
        cursor.execute("SELECT * FROM facts")
        for row in cursor.fetchall():
            data["facts"].append({
                "id": row[0],
                "category": row[1],
                "content": row[2],
                "source": row[3],
                "timestamp": row[4],
                "confidence": row[5]
            })
        
        conn.close()
        
        # Сохранение в файл
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
