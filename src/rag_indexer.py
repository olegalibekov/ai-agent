# rag_indexer.py

import requests
import numpy as np
import faiss
import pickle
import json
from typing import List, Dict
from pathlib import Path


class OllamaRAG:
    def __init__(self,
                 embedding_model='nomic-embed-text',
                 ollama_url='http://localhost:11434'):
        self.embedding_model = embedding_model
        self.ollama_url = ollama_url
        self.index = None
        self.chunks = []
        self.metadata = []

    def get_embedding(self, text: str) -> np.ndarray:
        """Получение эмбеддинга через Ollama"""
        response = requests.post(
            f'{self.ollama_url}/api/embeddings',
            json={
                'model': self.embedding_model,
                'prompt': text
            }
        )
        return np.array(response.json()['embedding'])

    def chunk_text(self, text: str, chunk_size=1000, overlap=100) -> List[str]:
        """Разбивка текста на чанки с перекрытием (500-1000 токенов)"""
        # Простой подсчёт токенов (примерно 4 символа = 3.txt токен)
        char_per_token = 4
        chunk_chars = chunk_size * char_per_token
        overlap_chars = overlap * char_per_token

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_chars

            # Пытаемся разбить по параграфам или предложениям
            chunk = text[start:end]

            # Если не конец текста, ищем ближайший конец предложения
            if end < len(text):
                last_period = chunk.rfind('.')
                last_newline = chunk.rfind('\n')
                split_point = max(last_period, last_newline)

                if split_point > len(chunk) * 0.5:  # Не слишком короткий чанк
                    chunk = chunk[:split_point + 1]
                    end = start + split_point + 1

            if chunk.strip():
                chunks.append(chunk.strip())

            start = end - overlap_chars

        return chunks

    def add_documents(self, documents: List[Dict[str, str]]):
        """Добавление документов в индекс"""
        print(f"Обработка {len(documents)} документов...")

        all_embeddings = []

        for doc in documents:
            print(f"\nОбработка: {doc['source']}")
            chunks = self.chunk_text(doc['text'], chunk_size=800, overlap=80)
            print(f"  Создано {len(chunks)} чанков")

            for i, chunk in enumerate(chunks):
                # Генерация эмбеддинга
                embedding = self.get_embedding(chunk)
                all_embeddings.append(embedding)

                # Сохранение чанка и метаданных
                self.chunks.append(chunk)
                self.metadata.append({
                    'source': doc['source'],
                    'chunk_id': i,
                    'total_chunks': len(chunks)
                })

                if (i + 1) % 10 == 0:
                    print(f"  Обработано {i + 1}/{len(chunks)} чанков")

        # Создание FAISS индекса
        embeddings_array = np.array(all_embeddings).astype('float32')

        # Нормализация векторов к [0, 3.txt]
        norms = np.linalg.norm(embeddings_array, axis=1, keepdims=True)
        embeddings_array = embeddings_array / norms

        dimension = embeddings_array.shape[1]
        self.index = faiss.IndexFlatIP(dimension)  # Inner Product для нормализованных векторов
        self.index.add(embeddings_array)

        print(f"\n✓ Индекс создан: {len(self.chunks)} чанков, размерность {dimension}")

    def search(self, query: str, top_k=5) -> List[Dict]:
        """Поиск релевантных чанков"""
        if self.index is None:
            raise ValueError("Индекс не создан. Сначала вызовите add_documents() или load()")

        query_embedding = self.get_embedding(query)
        query_embedding = query_embedding / np.linalg.norm(query_embedding)

        distances, indices = self.index.search(
            query_embedding.reshape(1, -1).astype('float32'),
            top_k
        )

        results = []
        for score, idx in zip(distances[0], indices[0]):
            results.append({
                'text': self.chunks[idx],
                'metadata': self.metadata[idx],
                'score': float(score)
            })

        return results

    def save(self, path='rag_index'):
        """Сохранение индекса в базу данных"""
        Path(path).mkdir(exist_ok=True)

        # Сохранение FAISS индекса
        faiss.write_index(self.index, f'{path}/vectors.faiss')

        # Сохранение чанков и метаданных
        with open(f'{path}/data.pkl', 'wb') as f:
            pickle.dump({
                'chunks': self.chunks,
                'metadata': self.metadata,
                'config': {
                    'embedding_model': self.embedding_model,
                    'total_chunks': len(self.chunks)
                }
            }, f)

        print(f"✓ Индекс сохранён в {path}/")

    def load(self, path='rag_index'):
        """Загрузка индекса из базы данных"""
        self.index = faiss.read_index(f'{path}/vectors.faiss')

        with open(f'{path}/data.pkl', 'rb') as f:
            data = pickle.load(f)
            self.chunks = data['chunks']
            self.metadata = data['metadata']

        print(f"✓ Загружен индекс: {len(self.chunks)} чанков")


def load_documents_from_folder(folder_path: str) -> List[Dict[str, str]]:
    """Загрузка всех документов из папки"""
    documents = []
    folder = Path(folder_path)

    if not folder.exists():
        print(f"⚠ Папка {folder_path} не найдена")
        return documents

    # Markdown и текстовые файлы
    for ext in ['*.md', '*.txt']:
        for file_path in folder.glob(ext):
            print(f"Загрузка {file_path.name}...")
            with open(file_path, 'r', encoding='utf-8') as f:
                documents.append({
                    'text': f.read(),
                    'source': file_path.name
                })

    # Python файлы (код)
    for file_path in folder.glob('*.py'):
        print(f"Загрузка {file_path.name}...")
        with open(file_path, 'r', encoding='utf-8') as f:
            documents.append({
                'text': f.read(),
                'source': file_path.name
            })

    # PDF файлы
    try:
        import pdfplumber
        for file_path in folder.glob('*.pdf'):
            print(f"Загрузка {file_path.name}...")
            with pdfplumber.open(file_path) as pdf:
                text = '\n'.join(page.extract_text() or '' for page in pdf.pages)
                documents.append({
                    'text': text,
                    'source': file_path.name
                })
    except ImportError:
        print("⚠ pdfplumber не установлен, PDF файлы пропущены")
        print("  Установите: pip install pdfplumber")

    print(f"\n✓ Загружено {len(documents)} документов")
    return documents


def main():
    """Основной пайплайн индексации"""
    print("=" * 80)
    print("RAG Индексация документов")
    print("=" * 80)

    # Создание RAG системы
    rag = OllamaRAG()

    # Загрузка документов из папки
    docs_folder = input("\nПуть к папке с документами (по умолчанию './documents'): ").strip()
    if not docs_folder:
        docs_folder = './documents'

    documents = load_documents_from_folder(docs_folder)

    if not documents:
        print("\n❌ Документы не найдены. Создайте папку './documents' и добавьте туда файлы.")
        return

    # Индексация документов
    print("\n" + "=" * 80)
    print("Начало индексации...")
    print("=" * 80)
    rag.add_documents(documents)

    # Сохранение индекса
    index_path = input("\nПуть для сохранения индекса (по умолчанию 'rag_index'): ").strip()
    if not index_path:
        index_path = 'rag_index'

    rag.save(index_path)

    # Демо поиска
    print("\n" + "=" * 80)
    print("Тестовый поиск")
    print("=" * 80)

    while True:
        query = input("\nВаш вопрос (или 'exit' для выхода): ").strip()
        if query.lower() in ['exit', 'quit', 'выход']:
            break

        if not query:
            continue

        results = rag.search(query, top_k=3)

        print("\n" + "-" * 80)
        print("Результаты поиска:")
        print("-" * 80)

        for i, result in enumerate(results, 1):
            print(f"\n{i}. Источник: {result['metadata']['source']}")
            print(f"   Релевантность: {result['score']:.4f}")
            print(f"   Чанк: {result['metadata']['chunk_id'] + 1}/{result['metadata']['total_chunks']}")
            print(f"\n   {result['text'][:400]}...")

    print("\n✓ Готово!")


if __name__ == '__main__':
    main()