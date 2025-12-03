#!/usr/bin/env python3
"""
Support Assistant CLI
Интерфейс для работы с системой поддержки
"""
import argparse
import requests
import json
from pathlib import Path

BACKEND_URL = "http://localhost:8000"
CRM_URL = "http://localhost:8001"

class SupportCLI:
    def __init__(self):
        self.backend_url = BACKEND_URL
        self.crm_url = CRM_URL
    
    def index(self, kb_path):
        """Индексирует базу знаний"""
        print(f"📚 Индексирую базу знаний: {kb_path}\n")
        
        try:
            resp = requests.post(
                f"{self.backend_url}/index",
                json={"kb_path": kb_path},
                timeout=120
            )
            
            if resp.status_code == 200:
                result = resp.json()
                print(f"✓ {result['message']}")
                print(f"\n📊 Статистика:")
                print(f"  Всего чанков: {result['total_chunks']}")
                print(f"\n📄 Проиндексированные файлы:")
                for source in result['sources']:
                    print(f"  - {source}")
            else:
                print(f"✗ Ошибка: {resp.text}")
        except Exception as e:
            print(f"✗ Ошибка подключения: {e}")
    
    def ask(self, user_id, question):
        """Задать вопрос от имени пользователя"""
        print(f"🔍 Обрабатываю вопрос от {user_id}...\n")
        
        try:
            # 1. Получаем информацию о пользователе
            print("📊 Загружаю контекст пользователя...")
            user_resp = requests.get(f"{self.crm_url}/crm/user/{user_id}")
            
            user_context = None
            if user_resp.status_code == 200:
                user = user_resp.json()
                print(f"  ✓ {user['name']} ({user['email']})")
                print(f"    План: {user['plan']}, Статус: {user['status']}")
                
                # Получаем открытые тикеты
                tickets_resp = requests.get(
                    f"{self.crm_url}/crm/user/{user_id}/tickets",
                    params={"status": "open"}
                )
                
                open_tickets = []
                if tickets_resp.status_code == 200:
                    tickets_data = tickets_resp.json()
                    open_tickets = tickets_data['tickets']
                    if open_tickets:
                        print(f"    Открытые тикеты: {len(open_tickets)}")
                        for ticket in open_tickets[:3]:
                            print(f"      - {ticket['id']}: {ticket['subject']}")
                
                # Формируем полный контекст для Backend
                user_context = {
                    'user': user,
                    'tickets': open_tickets
                }
            else:
                print(f"  ⚠️ Пользователь не найден, продолжаю без контекста")
                user = None
            
            # 2. Задаем вопрос в RAG с полным контекстом
            print(f"\n📚 Ищу ответ в базе знаний...")
            
            request_data = {
                "query": question,
                "user_id": user_id
            }
            
            # Добавляем контекст если есть
            if user_context:
                request_data["user_context"] = user_context
            
            answer_resp = requests.post(
                f"{self.backend_url}/ask",
                json=request_data,
                timeout=60
            )
            
            if answer_resp.status_code == 200:
                result = answer_resp.json()
                
                print("\n" + "="*60)
                print("💬 ОТВЕТ АССИСТЕНТА")
                print("="*60 + "\n")
                print(result['response'])
                
                if result['sources']:
                    print(f"\n📚 Источники:")
                    for source in result['sources']:
                        print(f"  - {source}")
                
                # 3. Предлагаем создать тикет если нужно
                if user and "тикет" not in question.lower():
                    print("\n" + "─"*60)
                    create = input("\n❓ Создать тикет для отслеживания? (y/n): ")
                    if create.lower() == 'y':
                        self._create_ticket_interactive(user_id, question, result['response'])
            else:
                print(f"✗ Ошибка: {answer_resp.text}")
                
        except Exception as e:
            print(f"✗ Ошибка: {e}")
    
    def _create_ticket_interactive(self, user_id, subject, description):
        """Интерактивное создание тикета"""
        categories = ["authentication", "billing", "sync", "storage", "api", "how_to", "other"]
        priorities = ["low", "medium", "high"]
        
        print("\n📋 Создание тикета:")
        print("\nКатегории:")
        for i, cat in enumerate(categories, 1):
            print(f"  {i}. {cat}")
        
        cat_choice = input(f"Выберите категорию (1-{len(categories)}): ")
        try:
            category = categories[int(cat_choice) - 1]
        except:
            category = "other"
        
        print("\nПриоритет:")
        for i, pri in enumerate(priorities, 1):
            print(f"  {i}. {pri}")
        
        pri_choice = input(f"Выберите приоритет (1-{len(priorities)}, по умолчанию medium): ")
        try:
            priority = priorities[int(pri_choice) - 1]
        except:
            priority = "medium"
        
        # Создаем тикет
        ticket_data = {
            "user_id": user_id,
            "subject": subject[:100],  # Ограничиваем длину
            "description": f"Вопрос: {subject}\n\nПредложенное решение:\n{description[:500]}",
            "category": category,
            "priority": priority
        }
        
        resp = requests.post(
            f"{self.crm_url}/crm/ticket",
            json=ticket_data
        )
        
        if resp.status_code == 200:
            result = resp.json()
            ticket_id = result['ticket_id']
            print(f"\n✅ Тикет создан: {ticket_id}")
        else:
            print(f"\n✗ Ошибка создания тикета: {resp.text}")
    
    def ticket(self, ticket_id):
        """Показать детали тикета"""
        print(f"📋 Загружаю тикет {ticket_id}...\n")
        
        try:
            resp = requests.get(f"{self.crm_url}/crm/ticket/{ticket_id}")
            
            if resp.status_code == 200:
                data = resp.json()
                ticket = data['ticket']
                user = data['user']
                
                print("="*60)
                print(f"📋 Тикет: {ticket['id']}")
                print("="*60)
                print(f"\n👤 Пользователь: {user['name']} ({user['email']})")
                print(f"   План: {user['plan']}")
                print(f"\n📌 Тема: {ticket['subject']}")
                print(f"📝 Описание:\n   {ticket['description']}")
                print(f"\n📊 Статус: {ticket['status']}")
                print(f"⚠️  Приоритет: {ticket['priority']}")
                print(f"📂 Категория: {ticket['category']}")
                print(f"👥 Назначен: {ticket['assigned_to']}")
                print(f"📅 Создан: {ticket['created']}")
                print(f"🔄 Обновлен: {ticket['updated']}")
                
                if ticket.get('resolution'):
                    print(f"\n✅ Решение: {ticket['resolution']}")
                
                # Предлагаем AI решение
                print("\n" + "─"*60)
                suggest = input("\n❓ Получить AI рекомендацию по решению? (y/n): ")
                if suggest.lower() == 'y':
                    self._suggest_solution(ticket_id, ticket)
            else:
                print(f"✗ Ошибка: {resp.text}")
        except Exception as e:
            print(f"✗ Ошибка: {e}")
    
    def _suggest_solution(self, ticket_id, ticket):
        """Предлагает AI решение для тикета"""
        print("\n🤖 Генерирую рекомендацию...")
        
        query = f"{ticket['subject']}. {ticket['description']}"
        
        try:
            resp = requests.post(
                f"{self.backend_url}/ask",
                json={"query": query, "user_id": ticket['user_id']},
                timeout=60
            )
            
            if resp.status_code == 200:
                result = resp.json()
                
                print("\n" + "="*60)
                print("💡 РЕКОМЕНДУЕМОЕ РЕШЕНИЕ")
                print("="*60 + "\n")
                print(result['response'])
                
                # Предлагаем обновить тикет
                print("\n" + "─"*60)
                update = input("\n❓ Добавить решение в тикет? (y/n): ")
                if update.lower() == 'y':
                    update_resp = requests.put(
                        f"{self.crm_url}/crm/ticket/{ticket_id}",
                        json={"resolution": result['response'][:500]}
                    )
                    
                    if update_resp.status_code == 200:
                        print("✅ Тикет обновлен")
                    else:
                        print(f"✗ Ошибка обновления: {update_resp.text}")
        except Exception as e:
            print(f"✗ Ошибка: {e}")
    
    def user(self, user_id):
        """Показать информацию о пользователе"""
        print(f"👤 Загружаю информацию о {user_id}...\n")
        
        try:
            # Информация о пользователе
            user_resp = requests.get(f"{self.crm_url}/crm/user/{user_id}")
            
            if user_resp.status_code != 200:
                print(f"✗ Пользователь не найден: {user_resp.text}")
                return
            
            user = user_resp.json()
            
            print("="*60)
            print(f"👤 Пользователь: {user['name']}")
            print("="*60)
            print(f"\n📧 Email: {user['email']}")
            print(f"💳 План: {user['plan']}")
            print(f"📊 Статус: {user['status']}")
            print(f"📅 Регистрация: {user['joined']}")
            print(f"🔐 2FA: {'✓ Включен' if user.get('2fa_enabled') else '✗ Отключен'}")
            
            if user.get('storage_limit_gb'):
                usage_pct = (user['storage_used_gb'] / user['storage_limit_gb']) * 100
                print(f"\n💾 Хранилище: {user['storage_used_gb']:.1f} GB / {user['storage_limit_gb']} GB ({usage_pct:.0f}%)")
            else:
                print(f"\n💾 Хранилище: {user['storage_used_gb']:.1f} GB (Unlimited)")
            
            print(f"📱 Устройства: {user.get('devices', 0)}")
            
            if user.get('payment_method'):
                print(f"💳 Способ оплаты: {user['payment_method']}")
            
            if user.get('subscription_renews'):
                print(f"🔄 Продление: {user['subscription_renews']}")
            
            # Тикеты пользователя
            tickets_resp = requests.get(f"{self.crm_url}/crm/user/{user_id}/tickets")
            
            if tickets_resp.status_code == 200:
                tickets_data = tickets_resp.json()
                tickets = tickets_data['tickets']
                
                print(f"\n📋 Тикеты: {len(tickets)}")
                
                open_tickets = [t for t in tickets if t['status'] == 'open']
                if open_tickets:
                    print(f"\n  🔓 Открытые ({len(open_tickets)}):")
                    for ticket in open_tickets:
                        print(f"    - {ticket['id']}: {ticket['subject']} ({ticket['priority']})")
                
                in_progress = [t for t in tickets if t['status'] == 'in_progress']
                if in_progress:
                    print(f"\n  ⏳ В работе ({len(in_progress)}):")
                    for ticket in in_progress:
                        print(f"    - {ticket['id']}: {ticket['subject']}")
        except Exception as e:
            print(f"✗ Ошибка: {e}")
    
    def stats(self):
        """Показать статистику CRM"""
        print("📊 Загружаю статистику...\n")
        
        try:
            resp = requests.get(f"{self.crm_url}/crm/stats")
            
            if resp.status_code == 200:
                stats = resp.json()
                
                print("="*60)
                print("📊 СТАТИСТИКА СИСТЕМЫ")
                print("="*60)
                
                print(f"\n👥 Пользователи: {stats['users']['total']}")
                print("   По планам:")
                for plan, count in stats['users']['by_plan'].items():
                    print(f"     - {plan}: {count}")
                
                print(f"\n📋 Тикеты: {stats['tickets']['total']}")
                print(f"   🔓 Открытые: {stats['tickets']['open']}")
                print(f"   ⏳ В работе: {stats['tickets']['in_progress']}")
                print(f"   ✅ Решенные: {stats['tickets']['resolved']}")
            else:
                print(f"✗ Ошибка: {resp.text}")
        except Exception as e:
            print(f"✗ Ошибка: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="Support Assistant - AI помощник службы поддержки CloudDocs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:

  # Индексация базы знаний
  %(prog)s index knowledge_base/

  # Задать вопрос от имени пользователя
  %(prog)s ask user_001 "почему не работает синхронизация?"

  # Показать детали тикета
  %(prog)s ticket ticket_101

  # Информация о пользователе
  %(prog)s user user_001

  # Статистика системы
  %(prog)s stats
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Доступные команды')
    
    # Команда index
    index_parser = subparsers.add_parser('index', help='Индексировать базу знаний')
    index_parser.add_argument('path', help='Путь к базе знаний')
    
    # Команда ask
    ask_parser = subparsers.add_parser('ask', help='Задать вопрос')
    ask_parser.add_argument('user_id', help='ID пользователя')
    ask_parser.add_argument('question', help='Вопрос')
    
    # Команда ticket
    ticket_parser = subparsers.add_parser('ticket', help='Показать тикет')
    ticket_parser.add_argument('ticket_id', help='ID тикета')
    
    # Команда user
    user_parser = subparsers.add_parser('user', help='Информация о пользователе')
    user_parser.add_argument('user_id', help='ID пользователя')
    
    # Команда stats
    stats_parser = subparsers.add_parser('stats', help='Статистика системы')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    cli = SupportCLI()
    
    if args.command == 'index':
        cli.index(args.path)
    elif args.command == 'ask':
        cli.ask(args.user_id, args.question)
    elif args.command == 'ticket':
        cli.ticket(args.ticket_id)
    elif args.command == 'user':
        cli.user(args.user_id)
    elif args.command == 'stats':
        cli.stats()

if __name__ == "__main__":
    main()
