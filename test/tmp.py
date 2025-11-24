#!/usr/bin/env python3
"""Диагностика и исправление проблемы с Ollama embeddings"""

import subprocess
import sys
import time


def run_command(cmd, description):
    """Выполнение команды с выводом"""
    print(f"\n{'=' * 60}")
    print(description)
    print(f"{'=' * 60}")
    print(f"$ {' '.join(cmd)}\n")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)

        return result.returncode == 0
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


def main():
    print("""
╔════════════════════════════════════════════════════════════╗
║        Исправление проблемы с Ollama Embeddings            ║
╚════════════════════════════════════════════════════════════╝

Проблема: Ошибка 500 "EOF" при получении embeddings
Решение: Переустановка модели nomic-embed-text
    """)

    input("Нажмите Enter для начала исправления...")

    # Шаг 1: Удаление повреждённой модели
    print("\n📦 Шаг 1: Удаление текущей версии модели")
    run_command(
        ['ollama', 'rm', 'nomic-embed-text'],
        "Удаление nomic-embed-text"
    )

    # Небольшая пауза
    time.sleep(2)

    # Шаг 2: Свежая установка
    print("\n📥 Шаг 2: Установка свежей версии модели")
    print("⏳ Это займёт 2-5 минут (загрузка ~274 MB)...\n")

    success = run_command(
        ['ollama', 'pull', 'nomic-embed-text'],
        "Загрузка nomic-embed-text"
    )

    if not success:
        print("\n❌ Не удалось установить модель")
        print("\nПопробуйте вручную:")
        print("  1. Закройте все процессы Ollama")
        print("  2. ollama rm nomic-embed-text")
        print("  3. ollama pull nomic-embed-text")
        sys.exit(1)

    # Шаг 3: Проверка
    print("\n✅ Шаг 3: Проверка установки")
    run_command(
        ['ollama', 'list'],
        "Список установленных моделей"
    )

    # Шаг 4: Тест embeddings
    print("\n🧪 Шаг 4: Тестирование модели")

    test_code = '''
import requests
import json

try:
    response = requests.post(
        "http://localhost:11434/api/embeddings",
        json={"model": "nomic-embed-text", "prompt": "test"},
        timeout=30
    )

    if response.status_code == 200:
        data = response.json()
        embedding = data.get("embedding", [])
        print(f"✅ Модель работает!")
        print(f"   Размерность: {len(embedding)}")
        print(f"   Первые значения: {embedding[:5]}")
    else:
        print(f"❌ Ошибка {response.status_code}")
        print(f"   Ответ: {response.text}")
except Exception as e:
    print(f"❌ Ошибка: {e}")
'''

    with open('/tmp/test_ollama.py', 'w') as f:
        f.write(test_code)

    run_command(
        ['python3', '/tmp/test_ollama.py'],
        "Тест получения embeddings"
    )

    print("\n" + "=" * 60)
    print("✅ ГОТОВО!")
    print("=" * 60)
    print("\nТеперь запустите:")
    print("  python rag_indexer.py")
    print("\nИли протестируйте:")
    print("  python test_embeddings.py")


if __name__ == '__main__':
    main()