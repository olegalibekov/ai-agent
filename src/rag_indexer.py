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
        try:
            response = requests.post(
                f'{self.ollama_url}/api/embeddings',  # 👈 вместо /api/embeddings
                json={
                    'model': self.embedding_model,
                    'input': text,  # 👈 вместо prompt
                },
                timeout=60,
            )

            if response.status_code != 200:
                print(f"❌ Ollama вернула ошибку {response.status_code}")
                print("Ответ сервера:")
                print(response.text)
                response.raise_for_status()

            data = response.json()

            if 'embedding' not in data:
                print("❌ Ошибка: в ответе нет поля 'embedding'")
                print("Полный ответ:", data)
                raise KeyError("'embedding' not found in response")

            return np.array(data['embedding'], dtype=np.float32)

        except requests.exceptions.RequestException as e:
            print(f"❌ Ошибка подключения к Ollama: {e}")
            print("Убедитесь, что Ollama запущен: `ollama serve`")
            raise
        except KeyError:
            print(f"❌ Модель {self.embedding_model} не поддерживает embeddings или ответ другого формата.")
            raise

    def chunk_text(self, text: str, chunk_size=1000, overlap=100) -> List[str]:
        """Разбивка текста на чанки с перекрытием (500-1000 токенов)"""
        char_per_token = 4
        chunk_chars = chunk_size * char_per_token
        overlap_chars = overlap * char_per_token

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_chars
            chunk = text[start:end]

            if end < len(text):
                last_period = chunk.rfind('.')
                last_newline = chunk.rfind('\n')
                split_point = max(last_period, last_newline)

                if split_point > len(chunk) * 0.5:
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
                embedding = self.get_embedding(chunk)
                all_embeddings.append(embedding)

                self.chunks.append(chunk)
                self.metadata.append({
                    'source': doc['source'],
                    'chunk_id': i,
                    'total_chunks': len(chunks)
                })

                if (i + 1) % 10 == 0:
                    print(f"  Обработано {i + 1}/{len(chunks)} чанков")

        embeddings_array = np.array(all_embeddings).astype('float32')
        norms = np.linalg.norm(embeddings_array, axis=1, keepdims=True)
        embeddings_array = embeddings_array / norms

        dimension = embeddings_array.shape[1]
        self.index = faiss.IndexFlatIP(dimension)
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
        faiss.write_index(self.index, f'{path}/vectors.faiss')

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

    for ext in ['*.md', '*.txt']:
        for file_path in folder.glob(ext):
            print(f"Загрузка {file_path.name}...")
            with open(file_path, 'r', encoding='utf-8') as f:
                documents.append({
                    'text': f.read(),
                    'source': file_path.name
                })

    for file_path in folder.glob('*.py'):
        print(f"Загрузка {file_path.name}...")
        with open(file_path, 'r', encoding='utf-8') as f:
            documents.append({
                'text': f.read(),
                'source': file_path.name
            })

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
        pass

    print(f"\n✓ Загружено {len(documents)} документов")
    return documents


def main():
    """Основной пайплайн индексации"""
    print("=" * 80)
    print("RAG Индексация документов")
    print("=" * 80)

    rag = OllamaRAG()

    docs_folder = input("\nПуть к папке с документами (по умолчанию './documents'): ").strip()
    if not docs_folder:
        docs_folder = '/Users/fehty/PycharmProjects/ai-agent/documents/'

    documents = load_documents_from_folder(docs_folder)

    if not documents:
        print("\n❌ Документы не найдены.")
        return

    print("\n" + "=" * 80)
    print("Начало индексации...")
    print("=" * 80)

    try:
        rag.add_documents(documents)
    except Exception as e:
        print(f"\n❌ Ошибка при индексации: {e}")
        return

    index_path = input("\nПуть для сохранения индекса (по умолчанию 'rag_index'): ").strip()
    if not index_path:
        index_path = 'rag_index'

    rag.save(index_path)

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