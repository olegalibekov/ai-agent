#!/usr/bin/env python3
"""
Скрипт для демонстрации работы Dev Assistant
"""
import requests
import json
import time
from pathlib import Path

BACKEND_URL = "http://localhost:8000"
MCP_URL = "http://localhost:8001"

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def check_health():
    """Проверка работы сервисов"""
    print_section("Проверка сервисов")
    
    try:
        resp = requests.get(f"{BACKEND_URL}/health")
        print(f"✓ Backend: {resp.json()}")
    except Exception as e:
        print(f"✗ Backend недоступен: {e}")
        return False
    
    try:
        resp = requests.get(f"{MCP_URL}/health")
        print(f"✓ MCP Server: {resp.json()}")
    except Exception as e:
        print(f"✗ MCP Server недоступен: {e}")
        return False
    
    return True

def index_project(project_path):
    """Индексирует проект"""
    print_section(f"Индексация проекта: {project_path}")
    
    try:
        resp = requests.post(
            f"{BACKEND_URL}/index",
            json={"project_path": project_path}
        )
        result = resp.json()
        print(f"✓ Статус: {result['status']}")
        print(f"✓ Сообщение: {result['message']}")
        print(f"✓ Документы:")
        for doc in result['documents']:
            print(f"  - {doc}")
        return True
    except Exception as e:
        print(f"✗ Ошибка индексации: {e}")
        return False

def test_help_command(query):
    """Тестирует команду /help"""
    print_section(f"Команда: /help {query}")
    
    try:
        resp = requests.post(
            f"{BACKEND_URL}/chat",
            json={"content": f"/help {query}"}
        )
        result = resp.json()
        print("📝 Ответ:")
        print(result['response'])
        
        if 'sources' in result:
            print(f"\n📚 Источники:")
            for source in result['sources']:
                print(f"  - {source}")
        
        return True
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        return False

def test_git_branch(repo_path):
    """Тестирует получение информации о ветке"""
    print_section("Git: Текущая ветка")
    
    try:
        resp = requests.post(
            f"{MCP_URL}/git/branch",
            json={"repo_path": repo_path}
        )
        result = resp.json()
        print(f"🌿 Текущая ветка: {result['current_branch']}")
        print(f"🌿 Все ветки:")
        for branch in result['all_branches']:
            marker = "→" if branch == result['current_branch'] else " "
            print(f"  {marker} {branch}")
        return True
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        return False

def test_git_status(repo_path):
    """Тестирует получение статуса репозитория"""
    print_section("Git: Статус репозитория")
    
    try:
        resp = requests.post(
            f"{MCP_URL}/git/status",
            json={"repo_path": repo_path}
        )
        result = resp.json()
        print(f"🌿 Ветка: {result['branch']}")
        print(f"📝 Есть изменения: {result['is_dirty']}")
        
        if result['modified_files']:
            print(f"📝 Измененные файлы:")
            for file in result['modified_files']:
                print(f"  - {file}")
        
        if result['untracked_files']:
            print(f"❓ Неотслеживаемые файлы:")
            for file in result['untracked_files']:
                print(f"  - {file}")
        
        return True
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        return False

def main():
    print("""
    ╔═══════════════════════════════════════════╗
    ║   Dev Assistant - Демонстрация работы    ║
    ╚═══════════════════════════════════════════╝
    """)
    
    # Путь к тестовому проекту
    project_path = "/Users/fehty/StudioProjects/rag_check"
    
    # 1. Проверка сервисов
    if not check_health():
        print("\n⚠️  Запустите сервисы перед тестированием!")
        print("Backend: python backend/main.py")
        print("MCP: python mcp_server/git_mcp.py")
        return
    
    time.sleep(1)
    
    # 2. Индексация проекта
    if not index_project(project_path):
        return
    
    time.sleep(1)
    
    # 3. Тестирование команд /help
    test_queries = [
        "структура проекта",
        "как добавить зависимость",
        "правила стиля кода",
        "что такое StatefulWidget"
    ]
    
    for query in test_queries:
        test_help_command(query)
        time.sleep(2)
    
    # 4. Тестирование Git MCP
    test_git_branch(project_path)
    time.sleep(1)
    
    test_git_status(project_path)
    
    print_section("Тестирование завершено! ✓")

if __name__ == "__main__":
    main()
