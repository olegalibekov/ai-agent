import time
import re
from pathlib import Path
from typing import List, Dict, Optional

import requests
import numpy as np
import faiss
import pickle


class OllamaRAG:
    def __init__(
            self,
            embedding_model: str = 'nomic-embed-text',
            ollama_url: str = 'http://localhost:11434',
            auto_fallback: bool = True,
            similarity_threshold: float = 0.5,
    ):
        self.embedding_model = embedding_model
        self.ollama_url = ollama_url
        self.auto_fallback = auto_fallback
        self.index = None
        self.chunks: List[str] = []
        self.metadata: List[Dict] = []
        self.similarity_threshold = similarity_threshold

        # Альтернативные модели для embeddings (в порядке приоритета)
        self.fallback_models = [
            'nomic-embed-text',
            # 'mxbai-embed-large',
            # 'all-minilm',
        ]

    # ========= EMBEDDINGS =========

    def get_embedding(self, text: str, max_retries: int = 1) -> np.ndarray:
        """Получение эмбеддинга с truncation и retry через Ollama /api/embed"""
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

    def chunk_text(self, text: str, chunk_size: int = 100, overlap: int = 50) -> List[str]:
        """Разбивка текста на чанки.
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

    # ========= ПОИСК + ФИЛЬТРАЦИЯ =========

    def search(
            self,
            query: str,
            top_k: int = 5,
            min_score: Optional[float] = None,
    ) -> List[Dict]:
        """Поиск релевантных чанков.

        top_k: сколько кандидатов взять из FAISS.
        min_score: порог отсечения по косинусному сходству (если None — без фильтра).
        """
        if self.index is None:
            raise ValueError("Индекс не создан. Сначала вызовите add_documents() или load()")

        query_embedding = self.get_embedding(query)
        query_embedding = query_embedding / np.linalg.norm(query_embedding)

        distances, indices = self.index.search(
            query_embedding.reshape(1, -1).astype('float32'),
            top_k
        )

        results: List[Dict] = []
        for score, idx in zip(distances[0], indices[0]):
            if idx < 0:
                continue

            score = float(score)

            if min_score is not None and score < min_score:
                continue

            results.append({
                'text': self.chunks[idx],
                'metadata': self.metadata[idx],
                'score': score,
            })

        return results

    # ========= КОНТЕКСТ С ССЫЛКАМИ =========

    def _build_context_with_refs(
            self,
            results: List[Dict],
            max_context_chars: int = 8000,
    ) -> tuple[str, List[Dict]]:
        """
        Формирует контекст для LLM с пронумерованными источниками.

        Возвращает:
        - context: строка с блоками вида
          `[1] Источник: file.txt (чанк 1/3)\n...текст...`
        - used_chunks: список чанков, каждому добавлен ключ 'ref_id' (номер [N])
        """
        context_parts: List[str] = []
        used_chunks: List[Dict] = []
        total_len = 0

        for ref_id, r in enumerate(results, start=1):
            chunk = r["text"].strip()
            meta = r["metadata"]

            header = (
                f"[{ref_id}] Источник: {meta['source']} "
                f"(чанк {meta['chunk_id'] + 1}/{meta['total_chunks']})\n"
            )
            piece = header + chunk

            if total_len + len(piece) > max_context_chars:
                break

            context_parts.append(piece)
            total_len += len(piece) + 2

            r_with_id = dict(r)
            r_with_id["ref_id"] = ref_id
            used_chunks.append(r_with_id)

        context = "\n\n---\n\n".join(context_parts)
        return context, used_chunks

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

    # ========= ОТВЕТ С RAG (С ОБЯЗАТЕЛЬНЫМИ ССЫЛКАМИ) =========

    def answer_with_rag(
            self,
            question: str,
            model: str = "llama3",
            top_k: int = 5,
            max_context_chars: int = 8000,
            min_score: Optional[float] = None,
    ) -> Dict:
        """
        Ответ с использованием RAG и ОБЯЗАТЕЛЬНЫМИ ссылками на источники.
        """
        # 1. Поиск релевантных чанков
        raw_results = self.search(question, top_k=top_k, min_score=min_score)

        # 2. Контекст с номерами источников
        context, used_chunks = self._build_context_with_refs(
            raw_results,
            max_context_chars=max_context_chars,
        )

        # 3. Промпты
        system_prompt = (
            "Ты технический ассистент и работаешь в режиме RAG.\n"
            "Всегда отвечай СТРОГО на русском языке.\n"
            "Ты МОЖЕШЬ использовать только информацию из контекста.\n"
            "Если в контексте нет ответа на вопрос — честно скажи об этом и не выдумывай факты.\n\n"
            "Очень важные правила:\n"
            "1) Каждый важный факт в ответе должен сопровождаться ссылкой на источник "
            "в формате [N], где N — номер фрагмента из контекста.\n"
            "2) В конце ответа добавь раздел 'Источники:' и перечисли использованные номера с кратким описанием.\n"
            "3) Если контекст пустой или не содержит ответа, напиши, что не можешь ответить на основе базы, "
            "и не добавляй ссылок."
        )

        if context:
            context_block = (
                "Контекст (фрагменты документов с номерами [N]):\n"
                f"{context}"
            )
        else:
            context_block = "Контекст (фрагменты документов): [ПУСТО]"

        user_content = (
            f"Вопрос пользователя:\n{question}\n\n"
            f"{context_block}\n\n"
            "Сформируй ответ, строго следуя правилам:\n"
            "- Используй только информацию из контекста.\n"
            "- Для каждого важного утверждения добавляй ссылку вида [N].\n"
            "- В конце добавь раздел 'Источники:' с перечислением использованных номеров, "
            "например: 'Источники: [1], [3]'."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        answer = self._chat(messages, model=model)

        return {
            "answer": answer,
            "context": context,
            "chunks": used_chunks,  # здесь уже есть 'ref_id'
        }

    # ========= ОТВЕТ БЕЗ RAG (на будущее, не обязателен для задания) =========

    def answer_without_rag(
            self,
            question: str,
            model: str = "llama3",
    ) -> str:
        system_prompt = (
            "Ты технический ассистент. "
            "Отвечай строго на русском языке. "
            "Отвечай честно: если не знаешь ответа, так и скажи."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ]

        return self._chat(messages, model=model)

    # ========= СЕРИАЛИЗАЦИЯ ИНДЕКСА =========

    def save(self, path: str = 'rag_index'):
        """Сохранение индекса в базу данных"""
        Path(path).mkdir(exist_ok=True)
        faiss.write_index(self.index, f'{path}/vectors.faiss')

        with open(f'{path}/data.pkl', 'wb') as f:
            pickle.dump({
                'chunks': self.chunks,
                'metadata': self.metadata,
                'config': {
                    'embedding_model': self.embedding_model,
                    'total_chunks': len(self.chunks),
                    'similarity_threshold': self.similarity_threshold,
                }
            }, f)

        print(f"✓ Индекс сохранён в {path}/")

    def load(self, path: str = 'rag_index'):
        """Загрузка индекса из базы данных"""
        self.index = faiss.read_index(f'{path}/vectors.faiss')

        with open(f'{path}/data.pkl', 'rb') as f:
            data = pickle.load(f)
            self.chunks = data['chunks']
            self.metadata = data['metadata']
            config = data.get('config') or {}
            if 'similarity_threshold' in config:
                self.similarity_threshold = config['similarity_threshold']

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


# ========= MAIN (простая индексация + ручной режим вопросов) =========

def main():
    print("=" * 80)
    print("RAG Индексация документов (с обязательными ссылками на источники)")
    print("=" * 80)

    rag = OllamaRAG(similarity_threshold=0.8)

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
    print("Режим вопросов (RAG с обязательными ссылками). Введите 'exit' для выхода.")
    print("=" * 80)

    while True:
        query = input("\nВаш вопрос: ").strip()
        if query.lower() in ['exit', 'quit', 'выход']:
            break
        if not query:
            continue

        try:
            result = rag.answer_with_rag(
                question=query,
                model="llama3",
                top_k=5,
                max_context_chars=8000,
                min_score=rag.similarity_threshold,
            )
        except Exception as e:
            print(f"\n❌ Ошибка при запросе к LLM: {e}")
            continue

        answer = result["answer"]
        print("\n" + "-" * 80)
        print("Ответ модели:")
        print("-" * 80)
        print(answer)

        has_citations = re.search(r"\[\d+\]", answer) is not None
        print("\nПроверка ссылок: содержит ли ответ [N]? ->", "ДА" if has_citations else "НЕТ")

        if result["chunks"]:
            print("\nИспользованные источники:")
            for ch in result["chunks"]:
                meta = ch["metadata"]
                ref_id = ch.get("ref_id", "?")
                print(
                    f"  [{ref_id}] {meta['source']} "
                    f"(чанк {meta['chunk_id'] + 1}/{meta['total_chunks']}, score={ch['score']:.4f})"
                )

    print("\n✓ Готово!")


if __name__ == '__main__':
    main()
