"""
RAG Engine с использованием локальной Ollama модели
"""

import json
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

import faiss
import numpy as np
import requests


class RAGEngine:
    """Движок для RAG с Ollama эмбеддингами"""

    def __init__(self, config: dict):
        self.config = config

        # Параметры
        self.dimension = 768  # nomic-embed-text использует 768
        self.chunk_size = config.get('chunk_size', 1000)
        self.chunk_overlap = config.get('chunk_overlap', 200)
        self.top_k = config.get('top_k', 5)
        self.similarity_threshold = config.get('similarity_threshold', 0.7)

        # Ollama API
        self.ollama_url = "http://localhost:11434/api/embeddings"
        self.model_name = "nomic-embed-text"

        # Пути для хранения
        storage_path = Path(config['storage']['path'])
        storage_path.mkdir(parents=True, exist_ok=True)

        self.index_path = storage_path / "faiss_index.bin"
        self.metadata_path = storage_path / "metadata.pkl"

        # Загрузка или создание индекса
        self.index = self._load_or_create_index()
        self.metadata = self._load_metadata()

        print(f"📚 RAG Engine загружен с Ollama: {len(self.metadata)} документов")

    def _get_embedding(self, text: str) -> np.ndarray:
        """Получение эмбеддинга через Ollama"""
        try:
            response = requests.post(
                self.ollama_url,
                json={
                    "model": self.model_name,
                    "prompt": text
                },
                timeout=30
            )

            if response.status_code == 200:
                embedding = response.json()['embedding']
                return np.array(embedding, dtype='float32')
            else:
                print(f"Ошибка Ollama API: {response.status_code}")
                return np.zeros(self.dimension, dtype='float32')

        except Exception as e:
            print(f"Ошибка получения эмбеддинга: {e}")
            return np.zeros(self.dimension, dtype='float32')

    def _load_or_create_index(self) -> faiss.IndexFlatL2:
        """Загрузка или создание FAISS индекса"""
        if self.index_path.exists():
            try:
                return faiss.read_index(str(self.index_path))
            except Exception as e:
                print(f"Ошибка загрузки индекса: {e}")

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
        """Разбиение текста на чанки"""
        chunks = []
        words = text.split()

        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk = ' '.join(words[i:i + self.chunk_size])
            if chunk:
                chunks.append(chunk)

        return chunks

    async def add_document(self, text: str, metadata: Optional[Dict[str, Any]] = None):
        """Добавление документа в индекс"""
        chunks = self._chunk_text(text)

        for chunk in chunks:
            # Получение эмбеддинга через Ollama
            embedding = self._get_embedding(chunk)
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
        """Добавление множества документов"""
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
        """Поиск релевантных документов"""
        if self.index.ntotal == 0:
            return []

        k = top_k or self.top_k

        # Получение эмбеддинга запроса
        query_embedding = self._get_embedding(query)
        query_embedding = np.array([query_embedding]).astype('float32')

        # Поиск ближайших соседей
        distances, indices = self.index.search(query_embedding, min(k * 2, self.index.ntotal))

        # Фильтрация и сортировка результатов
        results = []
        for distance, idx in zip(distances[0], indices[0]):
            if idx == -1 or idx >= len(self.metadata):
                continue

            # Проверка порога похожести
            similarity = 1 / (1 + distance)
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

    async def get_document_count(self) -> int:
        """Получение количества документов"""
        return len(self.metadata)

    async def get_stats(self) -> Dict[str, Any]:
        """Получение статистики"""
        return {
            "total_documents": len(self.metadata),
            "index_size": self.index.ntotal,
            "dimension": self.dimension,
            "storage_path": str(self.config['storage']['path']),
            "model": "ollama/nomic-embed-text"
        }

    async def close(self):
        """Корректное завершение работы"""
        self._save_index()
        self._save_metadata()