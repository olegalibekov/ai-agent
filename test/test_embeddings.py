#!/usr/bin/env python3
"""Тест получения embeddings от Ollama"""

import requests
import numpy as np

from src.rag_indexer import OllamaRAG


def test_ollama_connection():
    """Проверка подключения к Ollama"""
    print("=" * 60)
    print("Тест подключения к Ollama")
    print("=" * 60)

    try:
        response = requests.get('http://localhost:11434/api/tags', timeout=5)
        print("✓ Ollama доступна")
        models = response.json().get('models', [])
        print(f"  Найдено моделей: {len(models)}")
        for model in models:
            print(f"  - {model.get('name', 'unknown')}")
        return True
    except Exception as e:
        print(f"✗ Ollama недоступна: {e}")
        print("\nЗапустите Ollama командой: ollama serve")
        return False


def test_embeddings_api():
    """Тест API embeddings"""
    print("\n" + "=" * 60)
    print("Тест API embeddings")
    print("=" * 60)

    test_texts = [
        "Это тестовый текст",
        "RAG архитектура",
        "Как оформить отпуск?"
    ]

    for text in test_texts:
        try:
            response = requests.post(
                'http://localhost:11434/api/embeddings',
                json={
                    'model': 'nomic-embed-text',
                    'prompt': text
                },
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                embedding = np.array(data['embedding'], dtype=np.float32)
                print(f"✓ '{text[:30]}...'")
                print(f"  Размерность: {len(embedding)}")
                print(f"  Норма: {np.linalg.norm(embedding):.4f}")
            else:
                print(f"✗ '{text}' - HTTP {response.status_code}")
                print(f"  Ответ: {response.text[:200]}")

        except Exception as e:
            print(f"✗ '{text}' - ошибка: {e}")


def test_rag_indexer():
    """Тест класса OllamaRAG"""
    print("\n" + "=" * 60)
    print("Тест класса OllamaRAG")
    print("=" * 60)

    try:


        rag = OllamaRAG()

        # Тест получения embedding
        text = "Тестовый запрос"
        embedding = rag.get_embedding(text)
        print(f"✓ Получен embedding")
        print(f"  Размерность: {len(embedding)}")
        print(f"  Тип: {embedding.dtype}")
        print(f"  Норма: {np.linalg.norm(embedding):.4f}")

        # Тест индексации
        documents = [
            {'text': 'RAG это архитектура для поиска', 'source': 'doc1'},
            # {'text': 'Chunking разбивает текст на части', 'source': 'doc2'},
            # {'text': 'FAISS используется для векторного поиска', 'source': 'doc3'}
        ]

        print("\n  Создание индекса...")
        rag.add_documents(documents)

        # Тест поиска
        print("\n  Тест поиска...")
        results = rag.search('что такое RAG?', top_k=2)

        for i, result in enumerate(results, 1):
            print(f"\n  {i}. {result['metadata']['source']}")
            print(f"     Релевантность: {result['score']:.4f}")
            print(f"     Текст: {result['text'][:50]}...")

        if results[0]['score'] > 0:
            print("\n✓ Поиск работает корректно!")
        else:
            print("\n✗ Релевантность = 0, есть проблема")

    except Exception as e:
        print(f"✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    if test_ollama_connection():
        test_embeddings_api()
        test_rag_indexer()
    else:
        print("\n⚠ Сначала запустите Ollama")