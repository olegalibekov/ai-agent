"""
RAG Engine для God Agent
Векторное хранилище с использованием FAISS
"""

import json
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


class RAGEngine:
    """Движок для Retrieval-Augmented Generation"""
    
    def __init__(self, config: dict):
        self.config = config
        
        # Инициализация модели эмбеддингов
        self.model = SentenceTransformer(
            'sentence-transformers/paraphrase-multilingual-mpnet-base-v2'
        )
        
        # Параметры
        self.dimension = 768
        self.chunk_size = config.get('chunk_size', 1000)
        self.chunk_overlap = config.get('chunk_overlap', 200)
        self.top_k = config.get('top_k', 5)
        self.similarity_threshold = config.get('similarity_threshold', 0.7)
        
        # Пути для хранения
        storage_path = Path(config['storage']['path'])
        storage_path.mkdir(parents=True, exist_ok=True)
        
        self.index_path = storage_path / "faiss_index.bin"
        self.metadata_path = storage_path / "metadata.pkl"
        
        # Загрузка или создание индекса
        self.index = self._load_or_create_index()
        self.metadata = self._load_metadata()
        
        print(f"📚 RAG Engine загружен: {len(self.metadata)} документов")
    
    def _load_or_create_index(self) -> faiss.IndexFlatL2:
        """Загрузка или создание FAISS индекса"""
        if self.index_path.exists():
            try:
                return faiss.read_index(str(self.index_path))
            except Exception as e:
                print(f"Ошибка загрузки индекса: {e}")
        
        # Создание нового индекса
        return faiss.IndexFlatL2(self.dimension)
    
    def _load_metadata(self) -> List[Dict[str, Any]]:
        """Загрузка метаданных документов"""
        if self.metadata_path.exists():
            try:
                with open(self.metadata_path, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"Ошибка загрузки метаданных: {e}")
        
        return []
    
    def _save_index(self):
        """Сохранение индекса"""
        try:
            faiss.write_index(self.index, str(self.index_path))
        except Exception as e:
            print(f"Ошибка сохранения индекса: {e}")
    
    def _save_metadata(self):
        """Сохранение метаданных"""
        try:
            with open(self.metadata_path, 'wb') as f:
                pickle.dump(self.metadata, f)
        except Exception as e:
            print(f"Ошибка сохранения метаданных: {e}")
    
    def _chunk_text(self, text: str) -> List[str]:
        """
        Разбиение текста на чанки
        
        Args:
            text: Исходный текст
        
        Returns:
            Список чанков
        """
        chunks = []
        words = text.split()
        
        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk = ' '.join(words[i:i + self.chunk_size])
            if chunk:
                chunks.append(chunk)
        
        return chunks
    
    async def add_document(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Добавление документа в индекс
        
        Args:
            text: Текст документа
            metadata: Метаданные (опционально)
        """
        # Разбиение на чанки
        chunks = self._chunk_text(text)
        
        for chunk in chunks:
            # Получение эмбеддинга
            embedding = self.model.encode([chunk])[0]
            embedding = np.array([embedding]).astype('float32')
            
            # Добавление в индекс
            self.index.add(embedding)
            
            # Сохранение метаданных
            chunk_metadata = {
                "content": chunk,
                "timestamp": datetime.now().isoformat(),
                **(metadata or {})
            }
            self.metadata.append(chunk_metadata)
        
        # Сохранение
        self._save_index()
        self._save_metadata()
    
    async def add_documents(self, documents: List[Dict[str, Any]]):
        """
        Добавление множества документов
        
        Args:
            documents: Список документов с полями 'text' и 'metadata'
        """
        for doc in documents:
            await self.add_document(
                text=doc.get('text', ''),
                metadata=doc.get('metadata')
            )
    
    async def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Поиск релевантных документов
        
        Args:
            query: Поисковый запрос
            top_k: Количество результатов
            filter_metadata: Фильтр по метаданным
        
        Returns:
            Список релевантных документов с оценками
        """
        if self.index.ntotal == 0:
            return []
        
        k = top_k or self.top_k
        
        # Получение эмбеддинга запроса
        query_embedding = self.model.encode([query])[0]
        query_embedding = np.array([query_embedding]).astype('float32')
        
        # Поиск ближайших соседей
        distances, indices = self.index.search(query_embedding, min(k * 2, self.index.ntotal))
        
        # Фильтрация и сортировка результатов
        results = []
        for distance, idx in zip(distances[0], indices[0]):
            if idx == -1 or idx >= len(self.metadata):
                continue
            
            # Проверка порога похожести
            similarity = 1 / (1 + distance)  # Преобразование расстояния в похожесть
            if similarity < self.similarity_threshold:
                continue
            
            metadata = self.metadata[idx]
            
            # Фильтрация по метаданным
            if filter_metadata:
                if not all(
                    metadata.get(k) == v
                    for k, v in filter_metadata.items()
                ):
                    continue
            
            results.append({
                "content": metadata["content"],
                "metadata": metadata,
                "similarity": float(similarity),
                "distance": float(distance)
            })
            
            if len(results) >= k:
                break
        
        return results
    
    async def delete_documents(self, filter_metadata: Dict[str, Any]):
        """
        Удаление документов по фильтру метаданных
        
        Args:
            filter_metadata: Фильтр для удаления
        """
        # Находим индексы для удаления
        indices_to_keep = []
        metadata_to_keep = []
        
        for idx, meta in enumerate(self.metadata):
            should_delete = all(
                meta.get(k) == v
                for k, v in filter_metadata.items()
            )
            
            if not should_delete:
                indices_to_keep.append(idx)
                metadata_to_keep.append(meta)
        
        # Пересоздаем индекс с сохраненными документами
        if indices_to_keep != list(range(len(self.metadata))):
            new_index = faiss.IndexFlatL2(self.dimension)
            
            for idx in indices_to_keep:
                # Получаем эмбеддинг из старого индекса
                vector = faiss.rev_swig_ptr(
                    self.index.reconstruct(idx),
                    self.dimension
                )
                new_index.add(np.array([vector]).astype('float32'))
            
            self.index = new_index
            self.metadata = metadata_to_keep
            
            # Сохранение
            self._save_index()
            self._save_metadata()
    
    async def clear(self):
        """Очистка всех документов"""
        self.index = faiss.IndexFlatL2(self.dimension)
        self.metadata = []
        self._save_index()
        self._save_metadata()
    
    async def get_document_count(self) -> int:
        """Получение количества документов"""
        return len(self.metadata)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Получение статистики"""
        return {
            "total_documents": len(self.metadata),
            "index_size": self.index.ntotal,
            "dimension": self.dimension,
            "storage_path": str(self.config['storage']['path'])
        }
    
    async def close(self):
        """Корректное завершение работы"""
        self._save_index()
        self._save_metadata()
