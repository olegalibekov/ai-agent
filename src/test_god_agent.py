"""
Тесты для God Agent
"""

import pytest
import asyncio
from pathlib import Path
import tempfile
import shutil

from god_agent import (
    RAGEngine,
    MemoryManager,
    TaskTracker,
    Task,
    TaskStatus,
    TaskPriority
)


# Fixtures

@pytest.fixture
def temp_dir():
    """Временная директория для тестов"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def rag_config(temp_dir):
    """Конфигурация для RAG"""
    return {
        'chunk_size': 500,
        'chunk_overlap': 100,
        'top_k': 3,
        'similarity_threshold': 0.5,
        'storage': {
            'path': temp_dir,
            'index_name': 'test_index'
        }
    }


@pytest.fixture
def memory_config(temp_dir):
    """Конфигурация для Memory"""
    return {
        'short_term': {'enabled': True, 'max_messages': 10},
        'long_term': {
            'enabled': True,
            'database': f'{temp_dir}/test_memory.db'
        }
    }


# RAG Engine Tests

@pytest.mark.asyncio
async def test_rag_add_document(rag_config):
    """Тест добавления документа в RAG"""
    rag = RAGEngine(rag_config)
    
    await rag.add_document(
        "Flutter - это UI фреймворк от Google",
        metadata={'type': 'test'}
    )
    
    count = await rag.get_document_count()
    assert count > 0
    
    await rag.close()


@pytest.mark.asyncio
async def test_rag_search(rag_config):
    """Тест поиска в RAG"""
    rag = RAGEngine(rag_config)
    
    # Добавление документов
    documents = [
        {'text': 'Flutter - UI фреймворк', 'metadata': {'id': 1}},
        {'text': 'Python - язык программирования', 'metadata': {'id': 2}},
        {'text': 'Django - веб фреймворк на Python', 'metadata': {'id': 3}}
    ]
    
    await rag.add_documents(documents)
    
    # Поиск
    results = await rag.search("фреймворк Python", top_k=2)
    
    assert len(results) > 0
    assert 'Python' in results[0]['content'] or 'Django' in results[0]['content']
    
    await rag.close()


@pytest.mark.asyncio
async def test_rag_persistence(rag_config, temp_dir):
    """Тест сохранения и загрузки RAG"""
    # Создание и заполнение
    rag1 = RAGEngine(rag_config)
    await rag1.add_document("Test document", metadata={'test': True})
    count1 = await rag1.get_document_count()
    await rag1.close()
    
    # Загрузка
    rag2 = RAGEngine(rag_config)
    count2 = await rag2.get_document_count()
    
    assert count1 == count2
    
    await rag2.close()


# Memory Manager Tests

@pytest.mark.asyncio
async def test_memory_short_term(memory_config):
    """Тест краткосрочной памяти"""
    memory = MemoryManager(memory_config)
    
    await memory.add_short_term("Hello", "Hi there!")
    
    history = memory.get_short_term()
    assert len(history) == 1
    assert history[0]['user'] == "Hello"


@pytest.mark.asyncio
async def test_memory_long_term(memory_config):
    """Тест долгосрочной памяти"""
    memory = MemoryManager(memory_config)
    
    await memory.save_interaction(
        user_input="Test question",
        agent_response="Test answer",
        session_id="test_session"
    )
    
    results = await memory.search_interactions(query="Test")
    assert len(results) > 0


@pytest.mark.asyncio
async def test_memory_facts(memory_config):
    """Тест сохранения фактов"""
    memory = MemoryManager(memory_config)
    
    await memory.save_fact(
        category="preferences",
        content="Loves Flutter development",
        confidence=0.9
    )
    
    facts = await memory.get_facts(category="preferences")
    assert len(facts) > 0
    assert facts[0]['content'] == "Loves Flutter development"


# Task Tracker Tests

def test_task_create():
    """Тест создания задачи"""
    tracker = TaskTracker(storage_path=":memory:")
    
    task = tracker.create_task(
        title="Test Task",
        description="Testing",
        priority=TaskPriority.HIGH
    )
    
    assert task.title == "Test Task"
    assert task.status == TaskStatus.TODO
    assert task.priority == TaskPriority.HIGH


def test_task_complete():
    """Тест завершения задачи"""
    tracker = TaskTracker(storage_path=":memory:")
    
    task = tracker.create_task("Test Task")
    task_id = task.id
    
    completed = tracker.complete_task(task_id)
    
    assert completed is not None
    assert completed.status == TaskStatus.DONE
    assert completed.completed_at is not None


def test_task_search():
    """Тест поиска задач"""
    tracker = TaskTracker(storage_path=":memory:")
    
    tracker.create_task("Flutter project", tags=["flutter", "mobile"])
    tracker.create_task("Python script", tags=["python"])
    
    results = tracker.search_tasks("Flutter")
    assert len(results) == 1
    assert results[0].title == "Flutter project"


def test_task_filter_by_status():
    """Тест фильтрации по статусу"""
    tracker = TaskTracker(storage_path=":memory:")
    
    task1 = tracker.create_task("Task 1")
    task2 = tracker.create_task("Task 2")
    
    tracker.complete_task(task1.id)
    
    todo = tracker.get_tasks_by_status(TaskStatus.TODO)
    done = tracker.get_tasks_by_status(TaskStatus.DONE)
    
    assert len(todo) == 1
    assert len(done) == 1


def test_task_statistics():
    """Тест статистики задач"""
    tracker = TaskTracker(storage_path=":memory:")
    
    tracker.create_task("Task 1", priority=TaskPriority.HIGH)
    tracker.create_task("Task 2", priority=TaskPriority.LOW)
    task3 = tracker.create_task("Task 3")
    tracker.complete_task(task3.id)
    
    stats = tracker.get_statistics()
    
    assert stats['total'] == 3
    assert stats['todo'] == 2
    assert stats['done'] == 1
    assert stats['by_priority']['high'] == 1
    assert stats['by_priority']['low'] == 1


# Integration Tests

@pytest.mark.asyncio
async def test_integration_memory_and_rag(memory_config, rag_config):
    """Интеграционный тест: Memory + RAG"""
    memory = MemoryManager(memory_config)
    rag = RAGEngine(rag_config)
    
    # Сохранение взаимодействия
    user_input = "Как работает BLoC в Flutter?"
    agent_response = "BLoC - это паттерн управления состоянием..."
    
    await memory.save_interaction(user_input, agent_response)
    
    # Добавление в RAG
    await rag.add_document(
        f"Q: {user_input}\nA: {agent_response}",
        metadata={'type': 'conversation'}
    )
    
    # Поиск в RAG
    results = await rag.search("Flutter BLoC")
    
    assert len(results) > 0
    assert 'BLoC' in results[0]['content']
    
    await memory.save_session(type('Context', (), {
        'session_id': 'test',
        'timestamp': '2024-01-01',
        'user_id': 'test',
        'context_data': {}
    })())
    
    await rag.close()


@pytest.mark.asyncio  
async def test_full_workflow(memory_config, rag_config):
    """Тест полного workflow"""
    memory = MemoryManager(memory_config)
    rag = RAGEngine(rag_config)
    tracker = TaskTracker(storage_path=":memory:")
    
    # 1. Сохранение взаимодействия
    await memory.save_interaction(
        "Создай задачу: Изучить Flutter",
        "Задача создана"
    )
    
    # 2. Создание задачи
    task = tracker.create_task(
        "Изучить Flutter",
        priority=TaskPriority.HIGH
    )
    
    # 3. Добавление в базу знаний
    await rag.add_document(
        "Flutter - кроссплатформенный фреймворк",
        metadata={'topic': 'flutter'}
    )
    
    # 4. Проверка
    assert task is not None
    assert await rag.get_document_count() > 0
    
    history = await memory.search_interactions()
    assert len(history) > 0
    
    await rag.close()


# Performance Tests

@pytest.mark.asyncio
@pytest.mark.slow
async def test_rag_performance(rag_config):
    """Тест производительности RAG"""
    import time
    
    rag = RAGEngine(rag_config)
    
    # Добавление большого количества документов
    documents = [
        {
            'text': f'Document {i} with some content about topic {i % 10}',
            'metadata': {'id': i}
        }
        for i in range(1000)
    ]
    
    start = time.time()
    await rag.add_documents(documents)
    add_time = time.time() - start
    
    # Поиск
    start = time.time()
    results = await rag.search("topic 5", top_k=10)
    search_time = time.time() - start
    
    print(f"\nPerformance:")
    print(f"Add 1000 docs: {add_time:.2f}s")
    print(f"Search: {search_time*1000:.2f}ms")
    
    assert search_time < 1.0  # Поиск должен быть < 1 секунды
    
    await rag.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
