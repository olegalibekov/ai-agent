"""
AI Assistant для разработчиков с RAG и MCP интеграцией
"""
import os
from pathlib import Path
from typing import List, Dict, Optional

import anthropic
import faiss
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

load_dotenv()

app = FastAPI(title="Dev Assistant API")

# CORS для Flutter web
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Глобальные переменные
embedding_model = None
faiss_index = None
documents = []
document_metadata = []


class Message(BaseModel):
    content: str
    project_path: Optional[str] = None


class IndexRequest(BaseModel):
    project_path: str


class RAGSystem:
    """Система RAG для индексации документации проекта"""

    def __init__(self):
        print("Инициализация RAG системы...")
        self.model = SentenceTransformer('all-mpnet-base-v2')
        self.index = None
        self.documents = []
        self.metadata = []

    def load_documents(self, project_path: str) -> List[Dict]:
        """Загружает документы из проекта"""
        docs = []
        project_path = Path(project_path)

        # Загружаем README
        readme_path = project_path / "README.md"
        if readme_path.exists():
            content = readme_path.read_text(encoding='utf-8')
            docs.append({
                'content': content,
                'source': 'README.md',
                'type': 'markdown'
            })
            print(f"✓ Загружен README.md")

        # Загружаем документацию из docs/
        docs_dir = project_path / "docs"
        if docs_dir.exists():
            for file in docs_dir.rglob("*.md"):
                try:
                    content = file.read_text(encoding='utf-8')
                    relative_path = file.relative_to(project_path)
                    docs.append({
                        'content': content,
                        'source': str(relative_path),
                        'type': 'markdown'
                    })
                    print(f"✓ Загружен {relative_path}")
                except Exception as e:
                    print(f"✗ Ошибка при загрузке {file}: {e}")

        # Загружаем pubspec.yaml
        pubspec_path = project_path / "pubspec.yaml"
        if pubspec_path.exists():
            content = pubspec_path.read_text(encoding='utf-8')
            docs.append({
                'content': content,
                'source': 'pubspec.yaml',
                'type': 'yaml'
            })
            print(f"✓ Загружен pubspec.yaml")

        # Загружаем основные .dart файлы из lib/
        lib_dir = project_path / "lib"
        if lib_dir.exists():
            for file in lib_dir.rglob("*.dart"):
                try:
                    content = file.read_text(encoding='utf-8')
                    relative_path = file.relative_to(project_path)
                    # Ограничиваем размер для больших файлов
                    if len(content) > 10000:
                        content = content[:10000] + "\n... (truncated)"
                    docs.append({
                        'content': content,
                        'source': str(relative_path),
                        'type': 'dart'
                    })
                    print(f"✓ Загружен {relative_path}")
                except Exception as e:
                    print(f"✗ Ошибка при загрузке {file}: {e}")

        return docs

    def chunk_text(self, text: str, chunk_size: int = 500) -> List[str]:
        """Разбивает текст на чанки"""
        words = text.split()
        chunks = []
        current_chunk = []
        current_size = 0

        for word in words:
            current_chunk.append(word)
            current_size += len(word) + 1

            if current_size >= chunk_size:
                chunks.append(' '.join(current_chunk))
                current_chunk = []
                current_size = 0

        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks

    def index_documents(self, docs: List[Dict]):
        """Индексирует документы в FAISS"""
        print(f"\nИндексация {len(docs)} документов...")

        all_chunks = []
        chunk_metadata = []

        for doc in docs:
            chunks = self.chunk_text(doc['content'])
            for i, chunk in enumerate(chunks):
                all_chunks.append(chunk)
                chunk_metadata.append({
                    'source': doc['source'],
                    'type': doc['type'],
                    'chunk_id': i,
                    'total_chunks': len(chunks)
                })

        print(f"Создано {len(all_chunks)} чанков")

        # Создаем эмбеддинги
        print("Создание эмбеддингов...")
        embeddings = self.model.encode(all_chunks, show_progress_bar=True)

        # Создаем FAISS индекс
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings.astype('float32'))

        self.documents = all_chunks
        self.metadata = chunk_metadata

        print(f"✓ Индексация завершена! {len(all_chunks)} чанков в индексе")

    def search(self, query: str, k: int = 3) -> List[Dict]:
        """Ищет релевантные документы"""
        if self.index is None or len(self.documents) == 0:
            return []

        query_embedding = self.model.encode([query])
        distances, indices = self.index.search(query_embedding.astype('float32'), k)

        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.documents):
                results.append({
                    'content': self.documents[idx],
                    'metadata': self.metadata[idx],
                    'distance': float(distances[0][i])
                })

        return results


# Инициализация RAG системы
rag_system = RAGSystem()


@app.post("/index")
async def index_project(request: IndexRequest):
    """Индексирует проект для RAG"""
    try:
        project_path = request.project_path
        if not os.path.exists(project_path):
            raise HTTPException(status_code=404, detail="Проект не найден")

        # Загружаем и индексируем документы
        docs = rag_system.load_documents(project_path)
        if not docs:
            raise HTTPException(status_code=400, detail="Документы не найдены")

        rag_system.index_documents(docs)

        return {
            "status": "success",
            "message": f"Проиндексировано документов: {len(docs)}",
            "documents": [d['source'] for d in docs]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
async def chat(message: Message):
    """Обрабатывает сообщения с поддержкой команды /help"""
    try:
        user_message = message.content.strip()

        # Обработка команды /help
        if user_message.startswith("/help"):
            query = user_message.replace("/help", "").strip()

            if not query:
                return {
                    "response": """🤖 **Dev Assistant - Команды помощи**

Используйте `/help <вопрос>` для получения информации о проекте.

**Примеры:**
- `/help структура проекта`
- `/help как добавить зависимость`
- `/help где находится main.dart`
- `/help какие есть виджеты`
- `/help правила стиля кода`

Я ищу ответы в документации проекта и подсказываю фрагменты кода!"""
                }

            # Поиск по RAG
            results = rag_system.search(query, k=3)

            if not results:
                return {
                    "response": "❌ Индекс пуст. Сначала проиндексируйте проект через /index"
                }

            # Формируем контекст из найденных документов
            context = "\n\n".join([
                f"📄 **{r['metadata']['source']}** (релевантность: {1 / (1 + r['distance']):.2f})\n```\n{r['content']}\n```"
                for r in results
            ])

            # Используем Claude для генерации ответа
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                return {
                    "response": f"⚠️ ANTHROPIC_API_KEY не установлен\n\n**Найденная информация:**\n\n{context}"
                }

            client = anthropic.Anthropic(api_key=api_key)

            prompt = f"""Ты - AI-ассистент разработчика Flutter. Используй найденную документацию для ответа на вопрос.

**Вопрос:** {query}

**Найденная документация:**
{context}

Дай краткий и понятный ответ, основываясь на документации. Если нужно, покажи примеры кода."""

            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )

            return {
                "response": response.content[0].text,
                "sources": [r['metadata']['source'] for r in results]
            }

        # Обычный чат
        return {
            "response": "Используйте команду `/help <вопрос>` для получения помощи по проекту."
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """Проверка здоровья сервиса"""
    return {
        "status": "ok",
        "indexed_documents": len(rag_system.documents),
        "model": "all-mpnet-base-v2"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
