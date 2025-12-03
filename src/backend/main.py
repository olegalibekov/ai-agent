"""
Support Assistant Backend
RAG система для поддержки пользователей CloudDocs
"""
import os
from pathlib import Path
from typing import List, Dict, Optional
import anthropic
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

from dotenv import load_dotenv

load_dotenv()

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events для FastAPI"""
    rag_system.initialize()
    yield

app = FastAPI(title="Support Assistant Backend", lifespan=lifespan)

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

class QueryRequest(BaseModel):
    query: str
    user_id: Optional[str] = None
    user_context: Optional[Dict] = None


class IndexRequest(BaseModel):
    kb_path: str


# ============================================================================
# RAG система
# ============================================================================

class SupportRAG:
    def __init__(self):
        self.model = None
        self.index = None
        self.documents = []
        self.embeddings = None
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')

        if not self.anthropic_api_key:
            print("⚠️ ANTHROPIC_API_KEY не установлен. AI ответы не будут работать.")

    def initialize(self):
        """Инициализация модели embeddings"""
        print("🔧 Инициализация RAG системы...")
        self.model = SentenceTransformer('all-mpnet-base-v2')
        print("✓ Модель загружена")

    def load_knowledge_base(self, kb_path: str) -> List[str]:
        """Загружает базу знаний из markdown файлов"""
        kb_path = Path(kb_path)
        documents = []
        file_paths = []

        print(f"📚 Загружаю базу знаний из {kb_path}...")

        # Рекурсивно загружаем все .md файлы
        for md_file in kb_path.rglob("*.md"):
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Разбиваем на чанки по заголовкам
                chunks = self._split_by_headers(content, str(md_file.name))
                documents.extend(chunks)
                file_paths.append(str(md_file.relative_to(kb_path)))

                print(f"  ✓ {md_file.name}: {len(chunks)} чанков")
            except Exception as e:
                print(f"  ✗ Ошибка загрузки {md_file.name}: {e}")

        print(f"✓ Загружено {len(documents)} чанков из {len(file_paths)} файлов")
        return documents

    def _split_by_headers(self, content: str, filename: str) -> List[Dict[str, str]]:
        """Разбивает документ на чанки по заголовкам"""
        chunks = []
        lines = content.split('\n')

        current_chunk = []
        current_header = filename

        for line in lines:
            if line.startswith('#'):
                # Сохраняем предыдущий чанк
                if current_chunk:
                    chunk_text = '\n'.join(current_chunk).strip()
                    if len(chunk_text) > 50:  # Минимальная длина чанка
                        chunks.append({
                            'text': chunk_text,
                            'source': filename,
                            'header': current_header
                        })

                # Начинаем новый чанк
                current_header = line.strip('#').strip()
                current_chunk = [line]
            else:
                current_chunk.append(line)

        # Добавляем последний чанк
        if current_chunk:
            chunk_text = '\n'.join(current_chunk).strip()
            if len(chunk_text) > 50:
                chunks.append({
                    'text': chunk_text,
                    'source': filename,
                    'header': current_header
                })

        return chunks

    def create_index(self, documents: List[Dict[str, str]]):
        """Создает FAISS индекс"""
        print("🔨 Создаю FAISS индекс...")

        self.documents = documents
        texts = [doc['text'] for doc in documents]

        # Создаем embeddings
        self.embeddings = self.model.encode(texts, show_progress_bar=True)

        # Создаем FAISS индекс
        dimension = self.embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(self.embeddings.astype('float32'))

        print(f"✓ Индекс создан: {len(documents)} документов")

    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        """Поиск релевантных документов"""
        if self.index is None:
            return []

        # Создаем embedding запроса
        query_embedding = self.model.encode([query])

        # Поиск в FAISS
        distances, indices = self.index.search(
            query_embedding.astype('float32'),
            top_k
        )

        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx < len(self.documents):
                doc = self.documents[idx]
                results.append({
                    'text': doc['text'],
                    'source': doc['source'],
                    'header': doc['header'],
                    'score': float(distance)
                })

        return results

    def generate_answer(self, query: str, context: List[Dict],
                        user_context: Optional[Dict] = None) -> str:
        """Генерирует ответ с помощью Claude"""
        if not self.anthropic_api_key:
            # Возвращаем сырой контекст если нет API ключа
            context_text = "\n\n---\n\n".join([
                f"**{doc['header']}** ({doc['source']})\n{doc['text'][:300]}..."
                for doc in context
            ])
            return f"📚 Найденная информация:\n\n{context_text}"

        # Формируем контекст
        context_text = "\n\n".join([
            f"# {doc['header']}\n{doc['text']}"
            for doc in context
        ])

        # Добавляем контекст пользователя
        user_info = ""
        if user_context:
            user_data = user_context.get('user', {})
            tickets = user_context.get('tickets', [])

            # Информация о пользователе
            storage_limit = user_data.get('storage_limit_gb')
            if storage_limit:
                storage_info = f"{user_data.get('storage_used_gb', 0)} GB из {storage_limit} GB"
            else:
                storage_info = f"{user_data.get('storage_used_gb', 0)} GB (безлимитно)"

            user_info = f"""
**Информация о пользователе:**
- Имя: {user_data.get('name', 'N/A')}
- Email: {user_data.get('email', 'N/A')}
- План: {user_data.get('plan', 'N/A')}
- Статус аккаунта: {user_data.get('status', 'N/A')}
- Хранилище: {storage_info}
- 2FA: {'включена' if user_data.get('2fa_enabled') else 'отключена'}
"""

            # Открытые тикеты
            if tickets:
                user_info += f"\n**Открытые тикеты пользователя ({len(tickets)}):**\n"
                for ticket in tickets[:3]:  # Показываем до 3 тикетов
                    user_info += f"- Тикет #{ticket['id']}: {ticket['subject']}\n"
                    user_info += f"  Приоритет: {ticket['priority']}, Категория: {ticket['category']}\n"
                    if ticket.get('description'):
                        user_info += f"  Описание: {ticket['description'][:150]}...\n"

        # Формируем промпт
        prompt = f"""Ты - ассистент службы поддержки CloudDocs (облачное хранилище).

{user_info}

**Вопрос пользователя:** {query}

**База знаний:**
{context_text}

**Инструкции:**
1. ОБЯЗАТЕЛЬНО упомяни если у пользователя есть открытые тикеты по этой теме
2. Учитывай план пользователя (Free/Premium/Enterprise) при ответе
3. Если это технический вопрос - дай пошаговое решение
4. Персонализируй ответ на основе статуса аккаунта
5. Будь дружелюбным и профессиональным
6. Используй только релевантную информацию из базы знаний

Формат ответа:
- Упомяни открытые тикеты (если есть)
- Прямой ответ на вопрос
- Пошаговое решение (если применимо)
- Рекомендации с учетом плана пользователя"""

        try:
            client = anthropic.Anthropic(api_key=self.anthropic_api_key)
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}]
            )

            return message.content[0].text
        except Exception as e:
            print(f"Ошибка Claude API: {e}")
            return f"Ошибка генерации ответа: {e}"


# ============================================================================
# Глобальная инстанция RAG
# ============================================================================

rag_system = SupportRAG()


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/health")
async def health():
    """Проверка здоровья сервиса"""
    return {
        "status": "ok",
        "service": "Support Assistant Backend",
        "rag_initialized": rag_system.model is not None,
        "documents_indexed": len(rag_system.documents) if rag_system.documents else 0
    }


@app.post("/index")
async def index_knowledge_base(request: IndexRequest):
    """Индексирует базу знаний"""
    try:
        kb_path = Path(request.kb_path)
        if not kb_path.exists():
            raise HTTPException(status_code=404, detail=f"Путь {kb_path} не найден")

        # Загружаем документы
        documents = rag_system.load_knowledge_base(kb_path)

        if not documents:
            raise HTTPException(status_code=400, detail="Не найдены документы для индексации")

        # Создаем индекс
        rag_system.create_index(documents)

        # Собираем статистику
        sources = set(doc['source'] for doc in documents)

        return {
            "message": "База знаний проиндексирована",
            "total_chunks": len(documents),
            "sources": list(sources),
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ask")
async def ask_question(request: QueryRequest):
    """Отвечает на вопрос пользователя"""
    try:
        if not rag_system.index:
            raise HTTPException(
                status_code=400,
                detail="База знаний не проиндексирована. Используйте /index"
            )

        # Используем переданный контекст пользователя
        user_context = request.user_context

        # Ищем релевантные документы
        relevant_docs = rag_system.search(request.query, top_k=3)

        if not relevant_docs:
            return {
                "response": "К сожалению, не нашел информации по вашему вопросу в базе знаний. Пожалуйста, свяжитесь с поддержкой напрямую.",
                "sources": [],
                "context": []
            }

        # Генерируем ответ с контекстом пользователя
        answer = rag_system.generate_answer(
            request.query,
            relevant_docs,
            user_context
        )

        # Формируем источники
        sources = list(set([
            f"{doc['source']} - {doc['header']}"
            for doc in relevant_docs
        ]))

        return {
            "response": answer,
            "sources": sources,
            "context": relevant_docs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
async def chat(request: QueryRequest):
    """Общий чат endpoint (совместимость с dev_assistant)"""
    return await ask_question(request)


# ============================================================================
# Запуск
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("🚀 Support Assistant Backend")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8000)
