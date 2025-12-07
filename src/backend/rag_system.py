"""
News RAG System
Проверка дубликатов и анализ трендов новостей
"""
import os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import json

class NewsRAG:
    def __init__(self, index_path: str = "data/news_index"):
        self.index_path = Path(index_path)
        self.index_path.mkdir(parents=True, exist_ok=True)
        
        self.model = None
        self.index = None
        self.news_items = []
        
    def initialize(self):
        """Инициализация модели и индекса"""
        print("🔧 Инициализация RAG системы...")
        self.model = SentenceTransformer('all-mpnet-base-v2')
        
        # Загружаем существующий индекс если есть
        self._load_index()
        
        print("✓ RAG система готова")
    
    def _load_index(self):
        """Загружает существующий индекс"""
        index_file = self.index_path / "news.index"
        data_file = self.index_path / "news_data.json"
        
        if index_file.exists() and data_file.exists():
            try:
                self.index = faiss.read_index(str(index_file))
                
                with open(data_file, 'r', encoding='utf-8') as f:
                    self.news_items = json.load(f)
                
                print(f"  ✓ Загружено {len(self.news_items)} новостей из индекса")
            except Exception as e:
                print(f"  ⚠️ Ошибка загрузки индекса: {e}")
                self._create_empty_index()
        else:
            self._create_empty_index()
    
    def _create_empty_index(self):
        """Создаёт пустой индекс"""
        dimension = 768  # all-mpnet-base-v2
        self.index = faiss.IndexFlatL2(dimension)
        self.news_items = []
        print("  ✓ Создан новый индекс")
    
    def _save_index(self):
        """Сохраняет индекс"""
        index_file = self.index_path / "news.index"
        data_file = self.index_path / "news_data.json"
        
        faiss.write_index(self.index, str(index_file))
        
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(self.news_items, f, ensure_ascii=False, indent=2)
    
    def add_news(self, news_item: Dict):
        """Добавляет новость в индекс"""
        # Создаём текст для эмбеддинга
        text = f"{news_item['title']} {news_item.get('description', '')}"
        
        # Создаём эмбеддинг
        embedding = self.model.encode([text])
        
        # Добавляем в FAISS
        self.index.add(embedding.astype('float32'))
        
        # Добавляем метаданные
        news_item['added_at'] = datetime.utcnow().isoformat()
        self.news_items.append(news_item)
        
        # Сохраняем
        self._save_index()
    
    def check_duplicate(self, title: str, description: str = "", 
                       similarity_threshold: float = 0.8) -> Optional[Dict]:
        """
        Проверяет является ли новость дубликатом
        
        Returns:
            Dict с похожей новостью если найден дубликат, иначе None
        """
        if self.index.ntotal == 0:
            return None
        
        # Создаём эмбеддинг для новой новости
        text = f"{title} {description}"
        query_embedding = self.model.encode([text])
        
        # Ищем похожие
        distances, indices = self.index.search(
            query_embedding.astype('float32'), 
            min(5, self.index.ntotal)
        )
        
        # Проверяем similarity (меньше distance = больше похожесть)
        for distance, idx in zip(distances[0], indices[0]):
            if idx < len(self.news_items):
                similarity = 1.0 / (1.0 + distance)
                
                if similarity >= similarity_threshold:
                    similar_news = self.news_items[idx].copy()
                    similar_news['similarity'] = float(similarity)
                    return similar_news
        
        return None
    
    def get_recent_news(self, hours: int = 24) -> List[Dict]:
        """Возвращает новости за последние N часов"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        recent = []
        for item in self.news_items:
            added_at = datetime.fromisoformat(item['added_at'])
            if added_at >= cutoff_time:
                recent.append(item)
        
        return recent
    
    def get_trending_topics(self, hours: int = 24, top_k: int = 5) -> List[str]:
        """Анализирует популярные темы за последние N часов"""
        recent = self.get_recent_news(hours)
        
        # Простой подсчёт слов в заголовках
        word_counts = {}
        
        for item in recent:
            words = item['title'].lower().split()
            for word in words:
                if len(word) > 3:  # Игнорируем короткие слова
                    word_counts[word] = word_counts.get(word, 0) + 1
        
        # Сортируем по частоте
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        
        return [word for word, count in sorted_words[:top_k]]
    
    def get_stats(self) -> Dict:
        """Возвращает статистику"""
        total = len(self.news_items)
        
        if total == 0:
            return {
                "total_news": 0,
                "last_24h": 0,
                "last_7d": 0
            }
        
        last_24h = len(self.get_recent_news(24))
        last_7d = len(self.get_recent_news(24 * 7))
        
        return {
            "total_news": total,
            "last_24h": last_24h,
            "last_7d": last_7d,
            "trending_topics": self.get_trending_topics(24, 3)
        }

# Пример использования
if __name__ == "__main__":
    rag = NewsRAG()
    rag.initialize()
    
    # Тестовая новость
    test_news = {
        "title": "Apple анонсировала новый iPhone 16",
        "description": "Компания представила флагманский смартфон с новыми возможностями",
        "url": "https://example.com/news/1",
        "source": "TechCrunch"
    }
    
    # Проверяем дубликат
    duplicate = rag.check_duplicate(test_news['title'], test_news['description'])
    
    if duplicate:
        print(f"⚠️ Найден дубликат (similarity: {duplicate['similarity']:.2f})")
        print(f"   Похожая новость: {duplicate['title']}")
    else:
        print("✓ Новость уникальная, добавляем в индекс")
        rag.add_news(test_news)
    
    # Статистика
    stats = rag.get_stats()
    print(f"\n📊 Статистика:")
    print(f"   Всего новостей: {stats['total_news']}")
    print(f"   За 24 часа: {stats['last_24h']}")
