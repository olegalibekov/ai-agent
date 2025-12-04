"""
Team Assistant Backend
RAG система для знаний о проекте
"""
import os
from pathlib import Path
from typing import List, Dict, Optional
from contextlib import asynccontextmanager
import anthropic
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# Модели данных
# ============================================================================

class QueryRequest(BaseModel):
    query: str
    context: Optional[Dict] = None

class IndexRequest(BaseModel):
    kb_path: str

# ============================================================================
# RAG система
# ============================================================================

class TeamRAG:
    def __init__(self):
        self.model = None
        self.index = None
        self.documents = []
        self.embeddings = None
        self.anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        
        if not self.anthropic_api_key:
            print("⚠️ ANTHROPIC_API_KEY не установлен")
    
    def initialize(self):
        """Инициализация модели"""
        print("🔧 Инициализация RAG системы...")
        self.model = SentenceTransformer('all-mpnet-base-v2')
        print("✓ Модель загружена")
    
    def load_knowledge_base(self, kb_path: str) -> List[Dict]:
        """Загружает базу знаний"""
        kb_path = Path(kb_path)
        documents = []
        
        print(f"📚 Загружаю базу знаний из {kb_path}...")
        
        # Загружаем все файлы
        for file_path in kb_path.rglob("*"):
            if file_path.is_file() and file_path.suffix in ['.md', '.py', '.txt']:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Определяем тип файла
                    file_type = "code" if file_path.suffix == '.py' else "docs"
                    
                    # Разбиваем на чанки
                    chunks = self._split_content(content, str(file_path.name), file_type)
                    documents.extend(chunks)
                    
                    print(f"  ✓ {file_path.relative_to(kb_path)}: {len(chunks)} чанков")
                except Exception as e:
                    print(f"  ✗ Ошибка {file_path.name}: {e}")
        
        print(f"✓ Загружено {len(documents)} чанков")
        return documents
    
    def _split_content(self, content: str, filename: str, file_type: str) -> List[Dict]:
        """Разбивает контент на чанки"""
        chunks = []
        
        if file_type == "code":
            # Разбиваем по функциям/классам
            lines = content.split('\n')
            current_chunk = []
            current_name = filename
            
            for line in lines:
                if line.startswith('def ') or line.startswith('class '):
                    # Сохраняем предыдущий чанк
                    if current_chunk:
                        chunk_text = '\n'.join(current_chunk).strip()
                        if len(chunk_text) > 50:
                            chunks.append({
                                'text': chunk_text,
                                'source': filename,
                                'type': 'code',
                                'name': current_name
                            })
                    
                    # Новый чанк
                    current_name = line.split('(')[0].replace('def ', '').replace('class ', '').strip()
                    current_chunk = [line]
                else:
                    current_chunk.append(line)
            
            # Последний чанк
            if current_chunk:
                chunk_text = '\n'.join(current_chunk).strip()
                if len(chunk_text) > 50:
                    chunks.append({
                        'text': chunk_text,
                        'source': filename,
                        'type': 'code',
                        'name': current_name
                    })
        else:
            # Разбиваем по заголовкам
            lines = content.split('\n')
            current_chunk = []
            current_header = filename
            
            for line in lines:
                if line.startswith('#'):
                    if current_chunk:
                        chunk_text = '\n'.join(current_chunk).strip()
                        if len(chunk_text) > 50:
                            chunks.append({
                                'text': chunk_text,
                                'source': filename,
                                'type': 'docs',
                                'header': current_header
                            })
                    
                    current_header = line.strip('#').strip()
                    current_chunk = [line]
                else:
                    current_chunk.append(line)
            
            if current_chunk:
                chunk_text = '\n'.join(current_chunk).strip()
                if len(chunk_text) > 50:
                    chunks.append({
                        'text': chunk_text,
                        'source': filename,
                        'type': 'docs',
                        'header': current_header
                    })
        
        return chunks
    
    def create_index(self, documents: List[Dict]):
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
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
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
                    'type': doc['type'],
                    'name': doc.get('name') or doc.get('header', ''),
                    'score': float(distance)
                })
        
        return results
    
    def generate_answer(self, query: str, context_docs: List[Dict], 
                       project_context: Optional[Dict] = None) -> str:
        """Генерирует ответ с помощью Claude"""
        if not self.anthropic_api_key:
            # Возвращаем сырой контекст
            context_text = "\n\n---\n\n".join([
                f"**{doc['name']}** ({doc['source']})\n{doc['text'][:300]}..."
                for doc in context_docs
            ])
            return f"📚 Найденная информация:\n\n{context_text}"
        
        # Формируем контекст из документов
        context_text = "\n\n".join([
            f"# {doc['name']} ({doc['type']})\n{doc['text']}"
            for doc in context_docs
        ])
        
        # Добавляем контекст проекта
        project_info = ""
        if project_context:
            sprint = project_context.get('sprint', {})
            blockers = project_context.get('blockers', {})
            
            project_info = f"""
**Текущий контекст проекта:**
- Спринт: {sprint.get('name', 'N/A')}
- Прогресс: {sprint.get('completion_percent', 0)}%
- Заблокированных задач: {blockers.get('blocked_tasks', 0)}
- Блокеров релиза: {blockers.get('release_blockers', 0)}
"""
        
        # Промпт
        prompt = f"""Ты - ассистент команды разработки проекта CloudDocs.

{project_info}

**Вопрос:** {query}

**База знаний проекта:**
{context_text}

**Инструкции:**
1. Отвечай на основе предоставленной базы знаний
2. Если это вопрос о коде - дай конкретные примеры из кодовой базы
3. Если это вопрос о задачах - учитывай текущий контекст проекта
4. Будь конкретным и практичным
5. Если нужно - ссылайся на конкретные файлы и функции

Формат ответа:
- Прямой ответ на вопрос
- Конкретные примеры из кода/документации
- Рекомендации (если применимо)"""

        try:
            client = anthropic.Anthropic(api_key=self.anthropic_api_key)
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return message.content[0].text
        except Exception as e:
            print(f"Ошибка Claude API: {e}")
            return f"Ошибка генерации ответа: {e}"

# ============================================================================
# FastAPI App
# ============================================================================

rag_system = TeamRAG()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events"""
    rag_system.initialize()
    yield

app = FastAPI(title="Team Assistant Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/health")
async def health():
    """Проверка здоровья"""
    return {
        "status": "ok",
        "service": "Team Assistant Backend",
        "rag_initialized": rag_system.model is not None,
        "documents_indexed": len(rag_system.documents)
    }

@app.post("/index")
async def index_knowledge_base(request: IndexRequest):
    """Индексирует базу знаний"""
    try:
        kb_path = Path(request.kb_path)
        if not kb_path.exists():
            raise HTTPException(status_code=404, detail=f"Путь {kb_path} не найден")
        
        documents = rag_system.load_knowledge_base(kb_path)
        
        if not documents:
            raise HTTPException(status_code=400, detail="Не найдены документы")
        
        rag_system.create_index(documents)
        
        # Статистика
        sources = set(doc['source'] for doc in documents)
        types = {}
        for doc in documents:
            doc_type = doc['type']
            types[doc_type] = types.get(doc_type, 0) + 1
        
        return {
            "message": "База знаний проиндексирована",
            "total_chunks": len(documents),
            "sources": list(sources),
            "types": types,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ask")
async def ask_question(request: QueryRequest):
    """Отвечает на вопрос о проекте"""
    try:
        if not rag_system.index:
            raise HTTPException(
                status_code=400,
                detail="База знаний не проиндексирована. Используйте /index"
            )
        
        # Поиск релевантных документов
        relevant_docs = rag_system.search(request.query, top_k=5)
        
        if not relevant_docs:
            return {
                "response": "Не нашел информации по этому вопросу в базе знаний.",
                "sources": [],
                "context": []
            }
        
        # Генерируем ответ
        answer = rag_system.generate_answer(
            request.query,
            relevant_docs,
            request.context
        )
        
        # Формируем источники
        sources = [
            f"{doc['source']} - {doc['name']}"
            for doc in relevant_docs
        ]
        
        return {
            "response": answer,
            "sources": sources,
            "context": relevant_docs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# Запуск
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("🚀 Team Assistant Backend")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
