#!/usr/bin/env python3
"""
CLI клиент для Dev Assistant
"""
import argparse

import requests

BACKEND_URL = "http://localhost:8000"
MCP_URL = "http://localhost:8001"

from dotenv import load_dotenv

class DevAssistantCLI:
    def __init__(self):
        self.backend_url = BACKEND_URL
        self.mcp_url = MCP_URL
        load_dotenv()
    
    def index(self, project_path):
        """Индексирует проект"""
        print(f"📚 Индексирую проект: {project_path}")
        
        try:
            resp = requests.post(
                f"{self.backend_url}/index",
                json={"project_path": project_path},
                timeout=60
            )
            
            if resp.status_code == 200:
                result = resp.json()
                print(f"✓ {result['message']}")
                print(f"\nПроиндексированные документы:")
                for doc in result['documents']:
                    print(f"  - {doc}")
            else:
                print(f"✗ Ошибка: {resp.text}")
        except Exception as e:
            print(f"✗ Ошибка подключения: {e}")
    
    def help(self, query, project_path=None):
        """Команда /help"""
        try:
            data = {"content": f"/help {query}"}
            if project_path:
                data["project_path"] = project_path
            
            resp = requests.post(
                f"{self.backend_url}/chat",
                json=data,
                timeout=30
            )
            
            if resp.status_code == 200:
                result = resp.json()
                print(result['response'])
                
                if 'sources' in result and result['sources']:
                    print(f"\n📚 Источники: {', '.join(result['sources'])}")
            else:
                print(f"✗ Ошибка: {resp.text}")
        except Exception as e:
            print(f"✗ Ошибка подключения: {e}")
    
    def git_branch(self, repo_path):
        """Показывает текущую ветку"""
        try:
            resp = requests.post(
                f"{self.mcp_url}/git/branch",
                json={"repo_path": repo_path}
            )
            
            if resp.status_code == 200:
                result = resp.json()
                print(f"🌿 Текущая ветка: {result['current_branch']}")
                print(f"\nВсе ветки:")
                for branch in result['all_branches']:
                    marker = "→" if branch == result['current_branch'] else " "
                    print(f"  {marker} {branch}")
            else:
                print(f"✗ Ошибка: {resp.text}")
        except Exception as e:
            print(f"✗ Ошибка подключения: {e}")
    
    def git_status(self, repo_path):
        """Показывает статус репозитория"""
        try:
            resp = requests.post(
                f"{self.mcp_url}/git/status",
                json={"repo_path": repo_path}
            )
            
            if resp.status_code == 200:
                result = resp.json()
                print(f"🌿 Ветка: {result['branch']}")
                print(f"📝 Есть изменения: {'Да' if result['is_dirty'] else 'Нет'}")
                
                if result.get('modified_files'):
                    print(f"\n📝 Измененные файлы:")
                    for file in result['modified_files']:
                        print(f"  - {file}")
                
                if result.get('untracked_files'):
                    print(f"\n❓ Неотслеживаемые файлы:")
                    for file in result['untracked_files']:
                        print(f"  - {file}")
                
                if result.get('staged_files'):
                    print(f"\n✓ Файлы в staging:")
                    for file in result['staged_files']:
                        print(f"  - {file}")
            else:
                print(f"✗ Ошибка: {resp.text}")
        except Exception as e:
            print(f"✗ Ошибка подключения: {e}")
    
    def git_diff(self, repo_path):
        """Показывает git diff последнего коммита"""
        try:
            resp = requests.post(
                f"{self.mcp_url}/git/diff",
                json={"repo_path": repo_path}
            )
            
            if resp.status_code == 200:
                result = resp.json()
                diff = result.get('diff', '')
                
                if diff:
                    print("📊 Git Diff (последний коммит):\n")
                    print(diff)
                else:
                    print("✓ Нет изменений")
            else:
                print(f"✗ Ошибка: {resp.text}")
        except Exception as e:
            print(f"✗ Ошибка подключения: {e}")
    
    def review(self, repo_path):
        """Code review с использованием RAG + MCP + Claude"""
        print(f"🔍 Запускаю code review для: {repo_path}\n")
        
        try:
            # 1. Получаем diff через MCP
            print("📊 Получаю изменения через MCP...")
            diff_resp = requests.post(
                f"{self.mcp_url}/git/diff",
                json={"repo_path": repo_path}
            )
            
            if diff_resp.status_code != 200:
                print(f"✗ Ошибка получения diff: {diff_resp.text}")
                return None
            
            diff = diff_resp.json().get('diff', '')
            if not diff:
                print("✓ Нет изменений для ревью")
                return None
            
            # 2. Получаем контекст через RAG (используем уже проиндексированный проект)
            print("📚 Получаю контекст проекта через RAG...")
            
            # Используем /help для получения контекста о code style и структуре
            context_resp = requests.post(
                f"{self.backend_url}/chat",
                json={"content": "/help правила стиля кода и структура проекта"},
                timeout=30
            )
            
            context = ""
            if context_resp.status_code == 200:
                context_result = context_resp.json()
                context = context_result.get('response', '')
            
            # 3. Формируем промпт для Claude через backend
            print("🤖 Анализирую код с помощью AI...")
            
            review_prompt = f"""Проведи code review следующих изменений.

**Контекст проекта и правила:**
{context}

**Изменения (git diff):**
```
{diff}
```

**Задачи:**
1. Найди потенциальные баги и ошибки
2. Проверь соответствие code style проекта
3. Предложи улучшения кода
4. Отметь хорошие практики, если есть

**Формат ответа:**
## 🐛 Найденные проблемы
## 💡 Предложения по улучшению
## ✅ Хорошие практики
## 📊 Общая оценка"""

            # Отправляем как обычное сообщение в chat
            review_resp = requests.post(
                f"{self.backend_url}/chat",
                json={"content": review_prompt},
                timeout=60
            )
            
            if review_resp.status_code == 200:
                result = review_resp.json()
                review_text = result['response']
                
                print("\n" + "="*60)
                print("📋 РЕЗУЛЬТАТЫ CODE REVIEW")
                print("="*60 + "\n")
                print(review_text)
                
                if 'sources' in result and result['sources']:
                    print(f"\n📚 Использованы источники: {', '.join(result['sources'])}")
                
                return review_text
            else:
                print(f"✗ Ошибка ревью: {review_resp.text}")
                return None
                
        except Exception as e:
            print(f"✗ Ошибка: {e}")
            return None
    
    def review_pr(self, repo_path, pr_number, DEV_ASSISTANT_GITHUB_TOKEN=None, repo_owner=None, repo_name=None):
        """Code review с комментированием в GitHub PR"""
        import os
        
        print(f"🔍 Запускаю code review для PR #{pr_number}\n")
        
        # Получаем review
        review_text = self.review(repo_path)
        
        if not review_text:
            print("✗ Не удалось получить результаты ревью")
            return
        
        # Комментируем в GitHub
        # if not DEV_ASSISTANT_GITHUB_TOKEN:
        DEV_ASSISTANT_GITHUB_TOKEN = os.getenv('DEV_ASSISTANT_GITHUB_TOKEN')

        if not DEV_ASSISTANT_GITHUB_TOKEN:
            print("\n⚠️ DEV_ASSISTANT_GITHUB_TOKEN не установлен")
            print("Для комментирования в PR установите токен:")
            print("export DEV_ASSISTANT_GITHUB_TOKEN='ghp_...'")
            print("\nРезультаты ревью выше ↑")
            return
        
        if not repo_owner or not repo_name:
            print("\n⚠️ Не указан owner/repo")
            print("Используйте: --owner USERNAME --repo REPONAME")
            return
        
        # Отправляем комментарий в GitHub
        print(f"\n💬 Отправляю комментарий в PR #{pr_number}...")

        print(f"\n💬 {repo_owner}")
        print(f"\n💬 {repo_name}")
        print(f"\n💬 {pr_number}")
        print("\n💬 RAW TOKEN LENGTH:", len(DEV_ASSISTANT_GITHUB_TOKEN) if DEV_ASSISTANT_GITHUB_TOKEN else None)
        print("💬 RAW TOKEN FIRST 8:", DEV_ASSISTANT_GITHUB_TOKEN[:8] if DEV_ASSISTANT_GITHUB_TOKEN else None)
        print("💬 RAW TOKEN LAST 4:", DEV_ASSISTANT_GITHUB_TOKEN[-4:] if DEV_ASSISTANT_GITHUB_TOKEN else None)

        github_api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues/{pr_number}/comments"

        comment_body = f"""## 🤖 AI Code Review

{review_text}

---
*Автоматический ревью от Dev Assistant*
"""

        try:
            response = requests.post(
                github_api_url,
                headers={
                    "Authorization": f"Bearer {DEV_ASSISTANT_GITHUB_TOKEN}",
                    "Accept": "application/vnd.github.v3+json"
                },
                json={"body": comment_body}
            )
            
            if response.status_code == 201:
                comment_url = response.json().get('html_url', '')
                print(f"✅ Комментарий добавлен: {comment_url}")
            else:
                print(f"✗ Ошибка при добавлении комментария: {response.status_code}")
                print(f"   {response.text}")
        except Exception as e:
            print(f"✗ Ошибка GitHub API: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="Dev Assistant - AI помощник для Flutter разработчиков",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:

  # Индексация проекта
  %(prog)s index /path/to/flutter/project

  # Вопросы о проекте
  %(prog)s help "структура проекта"
  %(prog)s help "как добавить зависимость"
  %(prog)s help "правила стиля кода"

  # Git информация (через MCP)
  %(prog)s git-branch /path/to/project
  %(prog)s git-status /path/to/project
  %(prog)s git-diff /path/to/project
  
  # AI Code Review (Day 21)
  %(prog)s review /path/to/project
  %(prog)s review-pr /path/to/project 123 --owner USERNAME --repo REPONAME
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Доступные команды')
    
    # Команда index
    index_parser = subparsers.add_parser('index', help='Индексировать проект')
    index_parser.add_argument('path', help='Путь к проекту')
    
    # Команда help
    help_parser = subparsers.add_parser('help', help='Задать вопрос о проекте')
    help_parser.add_argument('query', help='Вопрос')
    help_parser.add_argument('--project', help='Путь к проекту (опционально)')
    
    # Команда git-branch
    branch_parser = subparsers.add_parser('git-branch', help='Показать текущую ветку')
    branch_parser.add_argument('path', help='Путь к репозиторию')
    
    # Команда git-status
    status_parser = subparsers.add_parser('git-status', help='Показать статус репозитория')
    status_parser.add_argument('path', help='Путь к репозиторию')
    
    # Команда git-diff
    diff_parser = subparsers.add_parser('git-diff', help='Показать git diff (последний коммит)')
    diff_parser.add_argument('path', help='Путь к репозиторию')
    
    # Команда review (Day 21)
    review_parser = subparsers.add_parser('review', help='Code review с AI (RAG + MCP + Claude)')
    review_parser.add_argument('path', help='Путь к репозиторию')
    
    # Команда review-pr (Day 21 - с комментированием в GitHub)
    review_pr_parser = subparsers.add_parser('review-pr', help='Code review с комментарием в GitHub PR')
    review_pr_parser.add_argument('path', help='Путь к репозиторию')
    review_pr_parser.add_argument('pr_number', type=int, help='Номер Pull Request')
    review_pr_parser.add_argument('--owner', required=True, help='GitHub username/organization')
    review_pr_parser.add_argument('--repo', required=True, help='Название репозитория')
    review_pr_parser.add_argument('--token', help='GitHub token (или используйте $DEV_ASSISTANT_GITHUB_TOKEN)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    cli = DevAssistantCLI()
    
    if args.command == 'index':
        cli.index(args.path)
    elif args.command == 'help':
        cli.help(args.query, args.project)
    elif args.command == 'git-branch':
        cli.git_branch(args.path)
    elif args.command == 'git-status':
        cli.git_status(args.path)
    elif args.command == 'git-diff':
        cli.git_diff(args.path)
    elif args.command == 'review':
        cli.review(args.path)
    elif args.command == 'review-pr':
        cli.review_pr(
            args.path, 
            args.pr_number,
            DEV_ASSISTANT_GITHUB_TOKEN=args.token,
            repo_owner=args.owner,
            repo_name=args.repo
        )

if __name__ == "__main__":
    main()
