# rag_indexer.py
import time

import ollama  # можно удалить, если не используешь ollama.* напрямую
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
                 ollama_url='http://localhost:11434',
                 auto_fallback=True):
        self.embedding_model = embedding_model
        self.ollama_url = ollama_url
        self.auto_fallback = auto_fallback
        self.index = None
        self.chunks: List[str] = []
        self.metadata: List[Dict] = []

        # Альтернативные модели для embeddings (в порядке приоритета)
        self.fallback_models = [
            'nomic-embed-text',
            # 'mxbai-embed-large',
            # 'all-minilm',
        ]

    # ========= EMBEDDINGS =========

    def get_embedding(self, text: str, max_retries=1) -> np.ndarray:
        """Получение эмбеддинга с truncation и retry через Ollama /api/embed"""
        # Ограничиваем размер текста (nomic-embed-text: ~8192 токенов)
        max_chars = 8000 * 4  # ~8000 токенов * 4 символа на токен
        if len(text) > max_chars:
            text = text[:max_chars]
            print(f"⚠ Текст обрезан до {max_chars} символов")

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f'{self.ollama_url}/api/embed',
                    json={
                        'model': self.embedding_model,
                        'input': text,
                        'truncate': True,
                    },
                    timeout=60,
                )

                if response.status_code != 200:
                    if attempt < max_retries - 1:
                        print(f"⚠ Попытка {attempt + 1} не удалась, повтор...")
                        time.sleep(2)
                        continue

                    print(f"❌ Ollama вернула ошибку {response.status_code}")
                    print("Ответ:", response.text)
                    response.raise_for_status()

                data = response.json()

                if 'embeddings' not in data:
                    raise KeyError("embedding not found in response")

                vec = np.array(data['embeddings'][0], dtype=np.float32)

                if vec.size == 0:
                    raise ValueError("empty embedding")

                return vec

            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    print(f"⚠ Ошибка сети, попытка {attempt + 1}/{max_retries}...")
                    time.sleep(2)
                else:
                    print(f"❌ Ошибка после {max_retries} попыток: {e}")
                    raise

        raise RuntimeError("Не удалось получить эмбеддинг")

    # ========= ЧАНКИРОВАНИЕ =========

    def chunk_text(self, text: str, chunk_size=100, overlap=50) -> List[str]:
        """Разбивка текста на чанки (уменьшенный размер для надёжности).
        chunk_size/overlap: в токенах (примерно), пересчёт в символы.
        """
        char_per_token = 4
        chunk_chars = chunk_size * char_per_token
        overlap_chars = overlap * char_per_token

        chunks: List[str] = []
        start = 0

        while start < len(text):
            end = start + chunk_chars
            chunk = text[start:end]

            # Пытаемся аккуратно обрезать по точке или переводу строки
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

    # ========= ПОСТРОЕНИЕ ИНДЕКСА =========

    def add_documents(self, documents: List[Dict[str, str]]):
        """Добавление документов в индекс"""
        print(f"Обработка {len(documents)} документов...")

        all_embeddings = []

        for doc in documents:
            print(f"\nОбработка: {doc['source']}")
            chunks = self.chunk_text(doc['text'])
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

    # ========= ПОИСК =========

    def search(self, query: str, top_k=1) -> List[Dict]:
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

    # ========= LLM (CHAT) =========

    def _chat(self, messages, model: str = "llama3") -> str:
        """
        Вызов LLM через Ollama /api/chat (без стриминга).
        messages: список dict-ов вида {'role': 'user'|'system'|'assistant', 'content': '...'}
        """
        try:
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                },
                timeout=120,
            )

            if response.status_code != 200:
                print(f"❌ Ошибка LLM {response.status_code}")
                print("Ответ:", response.text)
                response.raise_for_status()

            data = response.json()
            return data["message"]["content"]
        except requests.exceptions.RequestException as e:
            print(f"❌ Ошибка при запросе к LLM: {e}")
            raise

    # ========= ОТВЕТ С RAG =========

    def answer_with_rag(
        self,
        question: str,
        model: str = "llama3",
        top_k: int = 1,
        max_context_chars: int = 8000,
    ) -> Dict:
        """
        Ответ с использованием RAG:
        - ищем релевантные чанки
        - добавляем их в контекст
        - отправляем запрос к LLM
        Возвращаем dict с ответом и использованными чанками.
        """
        # 1. Поиск релевантных чанков
        results = self.search(question, top_k=top_k)

        # 2. Собираем контекст
        context_chunks = []
        total_len = 0
        for r in results:
            chunk = r["text"]
            if total_len + len(chunk) > max_context_chars:
                break
            context_chunks.append(chunk)
            total_len += len(chunk)

        context = "\n\n---\n\n".join(context_chunks)

        # 3. Формируем сообщения для LLM
        system_prompt = (
            "Ты технический ассистент. "
            "Отвечай строго на русском языке. "
            "Отвечай только на основе предоставленного контекста, "
            "если это возможно. Если в контексте нет ответа — скажи об этом."
        )

        user_content = (
            f"Вопрос пользователя:\n{question}\n\n"
            f"Контекст (фрагменты документов):\n{context}\n\n"
            "Ответь максимально полезно."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        answer = self._chat(messages, model=model)

        return {
            "answer": answer,
            "context": context,
            "chunks": results,
        }

    # ========= ОТВЕТ БЕЗ RAG =========

    def answer_without_rag(
        self,
        question: str,
        model: str = "llama3",
    ) -> str:
        """
        Базовый ответ модели без какого-либо контекста (без RAG).
        """
        system_prompt = (
            "Ты умный технический ассистент. "
            "Отвечай строго на русском языке. "
            "Отвечай только на основе предоставленного контекста, "
            "если это возможно. Если в контексте нет ответа — честно скажи об этом."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ]

        return self._chat(messages, model=model)

    # ========= СРАВНЕНИЕ =========

    def compare_answers(
        self,
        question: str,
        model: str = "llama3",
        top_k: int = 1,
    ) -> Dict:
        """
        Возвращает ответы модели с RAG и без RAG для одного вопроса.
        """
        rag_result = self.answer_with_rag(
            question=question,
            model=model,
            top_k=top_k,
        )
        no_rag_answer = self.answer_without_rag(
            question=question,
            model=model,
        )

        return {
            "question": question,
            "rag_answer": rag_result["answer"],
            "rag_chunks": rag_result["chunks"],
            "rag_context": rag_result["context"],
            "no_rag_answer": no_rag_answer,
        }

    # ========= СЕРИАЛИЗАЦИЯ ИНДЕКСА =========

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


# ========= ЗАГРУЗКА ДОКУМЕНТОВ =========

def load_documents_from_folder(folder_path: str) -> List[Dict[str, str]]:
    """Загрузка всех документов из папки"""
    documents: List[Dict[str, str]] = []
    folder = Path(folder_path)

    if not folder.exists():
        print(f"⚠ Папка {folder_path} не найдена")
        return documents

    # .md и .txt
    for ext in ['*.md', '*.txt']:
        for file_path in folder.glob(ext):
            print(f"Загрузка {file_path.name}...")
            with open(file_path, 'r', encoding='utf-8') as f:
                documents.append({
                    'text': f.read(),
                    'source': file_path.name
                })

    # .py
    for file_path in folder.glob('*.py'):
        print(f"Загрузка {file_path.name}...")
        with open(file_path, 'r', encoding='utf-8') as f:
            documents.append({
                'text': f.read(),
                'source': file_path.name
            })

    # .pdf (если есть pdfplumber)
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


# ========= MAIN =========

def main():
    """Основной пайплайн индексации + агент с RAG/без RAG"""
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
    print("Тестовый поиск и сравнение ответов (RAG / без RAG)")
    print("=" * 80)

    while True:
        query = input("\nВаш вопрос (или 'exit' для выхода): ").strip()
        if query.lower() in ['exit', 'quit', 'выход']:
            break

        if not query:
            continue

        try:
            comparison = rag.compare_answers(query, model="llama3", top_k=1)
        except Exception as e:
            print(f"\n❌ Ошибка при запросе к LLM: {e}")
            continue

        print("\n" + "-" * 80)
        print("Вопрос:")
        print(query)

        print("\n" + "-" * 80)
        print("Ответ С RAG (с контекстом из документов):")
        print("-" * 80)
        print(comparison["rag_answer"])

        print("\n" + "-" * 80)
        print("Ответ БЕЗ RAG (чистая модель):")
        print("-" * 80)
        print(comparison["no_rag_answer"])

        print("\n" + "-" * 80)
        print("Использованные чанки (для RAG):")
        print("-" * 80)
        for i, r in enumerate(comparison["rag_chunks"], 1):
            meta = r["metadata"]
            print(
                f"\n[{i}] Источник: {meta['source']}, "
                f"чанк: {meta['chunk_id'] + 1}/{meta['total_chunks']}, "
                f"score: {r['score']:.4f}"
            )
            print(r["text"][:400] + "...")

    print("\n✓ Готово!")


if __name__ == '__main__':
    main()
