#!/usr/bin/env python3
"""Проверка и подготовка Ollama для RAG"""

import requests
import subprocess
import sys


def check_ollama_running():
    """Проверка, что Ollama запущена"""
    try:
        response = requests.get('http://localhost:11434/api/tags', timeout=3)
        return response.status_code == 200
    except:
        return False


def get_installed_models():
    """Получение списка установленных моделей"""
    try:
        response = requests.get('http://localhost:11434/api/tags', timeout=5)
        if response.status_code == 200:
            data = response.json()
            return [model['name'] for model in data.get('models', [])]
        return []
    except:
        return []


def pull_model(model_name):
    """Загрузка модели через ollama pull"""
    print(f"\n📦 Загрузка модели {model_name}...")
    print("Это может занять несколько минут...\n")

    try:
        result = subprocess.run(
            ['ollama', 'pull', model_name],
            capture_output=True,
            text=True,
            timeout=600  # 10 минут максимум
        )

        if result.returncode == 0:
            print(f"✓ Модель {model_name} успешно загружена")
            return True
        else:
            print(f"✗ Ошибка загрузки: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("✗ Превышено время ожидания загрузки")
        return False
    except FileNotFoundError:
        print("✗ Команда 'ollama' не найдена")
        print("Установите Ollama: https://ollama.ai/")
        return False


def test_embedding(model_name):
    """Тест получения embedding"""
    print(f"\n🧪 Тест модели {model_name}...")

    try:
        response = requests.post(
            'http://localhost:11434/api/embeddings',
            json={
                'model': model_name,
                'prompt': 'test'
            },
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            embedding = data.get('embedding', [])
            print(f"✓ Модель работает! Размерность: {len(embedding)}")
            return True
        else:
            print(f"✗ Ошибка {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Ошибка теста: {e}")
        return False


def main():
    print("=" * 70)
    print("Подготовка Ollama для RAG")
    print("=" * 70)

    # Шаг 1: Проверка Ollama
    print("\n1. Проверка Ollama...")
    if not check_ollama_running():
        print("✗ Ollama не запущена")
        print("\nЗапустите Ollama одним из способов:")
        print("  - macOS/Linux: ollama serve")
        print("  - Или запустите Ollama Desktop приложение")
        sys.exit(1)

    print("✓ Ollama запущена")

    # Шаг 2: Проверка установленных моделей
    print("\n2. Проверка установленных моделей...")
    models = get_installed_models()
    print(f"Найдено моделей: {len(models)}")
    for model in models:
        print(f"  - {model}")

    # Шаг 3: Проверка/установка nomic-embed-text
    print("\n3. Проверка модели для embeddings...")
    target_model = 'nomic-embed-text'

    model_found = any(target_model in model for model in models)

    if not model_found:
        print(f"⚠ Модель {target_model} не найдена")
        response = input(f"\nЗагрузить {target_model}? (y/n): ").strip().lower()

        if response == 'y':
            if pull_model(target_model):
                print("\n✓ Модель готова к использованию")
            else:
                print("\n✗ Не удалось загрузить модель")
                sys.exit(1)
        else:
            print("\n⚠ Без модели embeddings RAG не будет работать")
            sys.exit(1)
    else:
        print(f"✓ Модель {target_model} установлена")

    # Шаг 4: Финальный тест
    if test_embedding(target_model):
        print("\n" + "=" * 70)
        print("✅ Всё готово! Можно запускать rag_indexer.py")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("❌ Есть проблемы с моделью")
        print("=" * 70)
        print("\nПопробуйте переустановить:")
        print(f"  ollama rm {target_model}")
        print(f"  ollama pull {target_model}")


if __name__ == '__main__':
    main()