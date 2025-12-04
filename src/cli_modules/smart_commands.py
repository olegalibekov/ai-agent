"""
Team Assistant CLI - Smart Commands
Умные команды: приоритизация, рекомендации, анализ
"""
import requests
from typing import List, Dict

BACKEND_URL = "http://localhost:8000"
MCP_URL = "http://localhost:8001"

class SmartCommands:
    def __init__(self):
        self.backend_url = BACKEND_URL
        self.mcp_url = MCP_URL
    
    # ========================================================================
    # Вопросы о проекте (RAG)
    # ========================================================================
    
    def ask(self, question: str):
        """Задать вопрос о проекте"""
        print(f"🔍 Ищу ответ на вопрос...\n")
        
        try:
            # Загружаем контекст проекта
            project_resp = requests.get(f"{self.mcp_url}/project/status")
            project_context = project_resp.json() if project_resp.status_code == 200 else None
            
            # Задаем вопрос в RAG
            resp = requests.post(
                f"{self.backend_url}/ask",
                json={"query": question, "context": project_context},
                timeout=60
            )
            
            if resp.status_code == 200:
                result = resp.json()
                
                print("="*60)
                print("💬 ОТВЕТ")
                print("="*60 + "\n")
                print(result['response'])
                
                if result['sources']:
                    print(f"\n📚 Источники:")
                    for source in result['sources'][:3]:
                        print(f"  - {source}")
            else:
                print(f"✗ Ошибка: {resp.text}")
        except Exception as e:
            print(f"✗ Ошибка: {e}")
    
    # ========================================================================
    # Приоритизация задач
    # ========================================================================
    
    def prioritize(self):
        """AI приоритизация задач"""
        print("🤖 Анализирую задачи для приоритизации...\n")
        
        try:
            # Получаем все задачи
            tasks_resp = requests.get(f"{self.mcp_url}/tasks")
            if tasks_resp.status_code != 200:
                print("✗ Не удалось загрузить задачи")
                return
            
            tasks = tasks_resp.json()['tasks']
            
            # Фильтруем открытые и in_progress
            active_tasks = [t for t in tasks if t['status'] in ['open', 'in_progress', 'blocked']]
            
            # Получаем блокеры
            blockers_resp = requests.get(f"{self.mcp_url}/tasks/blockers/all")
            blockers_data = blockers_resp.json() if blockers_resp.status_code == 200 else {}
            
            # Статус проекта
            status_resp = requests.get(f"{self.mcp_url}/project/status")
            project_status = status_resp.json() if status_resp.status_code == 200 else {}
            
            print("📊 Текущая ситуация:")
            print(f"  Активных задач: {len(active_tasks)}")
            
            high_tasks = [t for t in active_tasks if t['priority'] == 'high']
            print(f"  High приоритет: {len(high_tasks)}")
            
            blocked_tasks = [t for t in active_tasks if t['status'] == 'blocked']
            if blocked_tasks:
                print(f"  Заблокировано: {len(blocked_tasks)}")
            
            release_blockers = blockers_data.get('release_blockers', [])
            if release_blockers:
                print(f"  Блокируют релиз: {len(release_blockers)}")
            
            # Формируем анализ для AI
            analysis_query = f"""Проанализируй задачи проекта и предложи приоритеты.

Активные задачи ({len(active_tasks)}):
{self._format_tasks_for_analysis(active_tasks[:10])}

Заблокированные задачи: {len(blocked_tasks)}
Блокеров релиза: {len(release_blockers)}

Задачи, блокирующие релиз:
{self._format_tasks_for_analysis(release_blockers)}

Вопрос: Какие 3 задачи нужно сделать первыми и почему? Учитывай:
1. Блокеры и зависимости
2. Приоритет и срочность
3. Влияние на релиз
4. Критичность (security issues, bugs)
"""
            
            # Отправляем в RAG для анализа
            resp = requests.post(
                f"{self.backend_url}/ask",
                json={"query": analysis_query, "context": project_status},
                timeout=60
            )
            
            if resp.status_code == 200:
                result = resp.json()
                
                print("\n" + "="*60)
                print("💡 РЕКОМЕНДАЦИИ ПО ПРИОРИТИЗАЦИИ")
                print("="*60 + "\n")
                print(result['response'])
            else:
                # Fallback: базовая приоритизация без AI
                self._basic_prioritization(active_tasks, blocked_tasks, release_blockers)
        except Exception as e:
            print(f"✗ Ошибка: {e}")
    
    def _format_tasks_for_analysis(self, tasks: List[Dict]) -> str:
        """Форматирует задачи для анализа"""
        if not tasks:
            return "Нет"
        
        result = []
        for task in tasks:
            blocks = task.get('blocks', [])
            blocked_by = task.get('blocked_by', [])
            cve = task.get('cve_severity')
            
            line = f"- {task['id']}: {task['title']}"
            line += f" [priority={task['priority']}, status={task['status']}]"
            
            if blocks:
                line += f" [блокирует: {', '.join(blocks)}]"
            if blocked_by:
                line += f" [блокируется: {', '.join(blocked_by)}]"
            if cve:
                line += f" [CVE severity={cve}]"
            if task.get('blocks_release'):
                line += " [BLOCKS RELEASE]"
            
            result.append(line)
        
        return '\n'.join(result)
    
    def _basic_prioritization(self, active_tasks: List[Dict], 
                             blocked_tasks: List[Dict],
                             release_blockers: List[Dict]):
        """Базовая приоритизация без AI"""
        print("\n" + "="*60)
        print("💡 БАЗОВЫЕ РЕКОМЕНДАЦИИ")
        print("="*60 + "\n")
        
        recommendations = []
        
        # 1. Release blockers
        for task in release_blockers:
            if task['status'] != 'blocked':
                recommendations.append({
                    'task': task,
                    'reason': '🚀 Блокирует релиз',
                    'priority': 1
                })
        
        # 2. Tasks with high CVE
        for task in active_tasks:
            if task.get('cve_severity', 0) >= 8.0:
                recommendations.append({
                    'task': task,
                    'reason': '🔐 Критическая уязвимость',
                    'priority': 1
                })
        
        # 3. Tasks blocking others
        for task in active_tasks:
            if task.get('blocks') and task['status'] != 'blocked':
                recommendations.append({
                    'task': task,
                    'reason': f"🔗 Блокирует {len(task['blocks'])} задач(и)",
                    'priority': 2
                })
        
        # Сортируем по приоритету
        recommendations.sort(key=lambda x: x['priority'])
        
        # Выводим топ-5
        for i, rec in enumerate(recommendations[:5], 1):
            task = rec['task']
            print(f"{i}. **{task['id']}: {task['title']}**")
            print(f"   {rec['reason']}")
            print(f"   Статус: {task['status']}, Приоритет: {task['priority']}")
            if task.get('assignee'):
                print(f"   Назначена: {task['assignee']}")
            print()
    
    # ========================================================================
    # Рекомендации "что делать дальше"
    # ========================================================================
    
    def recommend_next(self):
        """Рекомендует что делать первым"""
        print("🎯 Определяю следующий шаг...\n")
        
        try:
            # Получаем статус
            status_resp = requests.get(f"{self.mcp_url}/project/status")
            if status_resp.status_code != 200:
                print("✗ Не удалось загрузить статус проекта")
                return
            
            status = status_resp.json()
            
            # Получаем блокеры
            blockers_resp = requests.get(f"{self.mcp_url}/tasks/blockers/all")
            blockers = blockers_resp.json() if blockers_resp.status_code == 200 else {}
            
            # Получаем high priority задачи
            high_resp = requests.get(f"{self.mcp_url}/tasks", params={"priority": "high", "status": "open"})
            high_tasks = high_resp.json()['tasks'] if high_resp.status_code == 200 else []
            
            print("📊 Анализ ситуации:")
            print(f"  Прогресс спринта: {status['sprint']['completion_percent']}%")
            print(f"  Блокеров: {blockers.get('blocked_tasks', 0)}")
            print(f"  Блокируют релиз: {blockers.get('release_blockers', 0)}")
            print(f"  High priority открытых: {len(high_tasks)}")
            
            # Определяем рекомендацию
            print("\n" + "="*60)
            print("💡 РЕКОМЕНДАЦИЯ")
            print("="*60 + "\n")
            
            if blockers.get('release_blockers'):
                release_blocker_tasks = blockers['release_blockers']
                # Находим незаблокированные
                actionable = [t for t in release_blocker_tasks if t['status'] != 'blocked']
                
                if actionable:
                    task = actionable[0]
                    print(f"🚨 СРОЧНО: {task['id']}: {task['title']}")
                    print(f"\n📌 Причина:")
                    print(f"  - Блокирует релиз (запланирован на {status['sprint']['sprint']['release_date']})")
                    print(f"  - Статус: {task['status']}")
                    print(f"  - Приоритет: {task['priority']}")
                    if task.get('assignee'):
                        print(f"  - Назначена: {task['assignee']}")
                    else:
                        print(f"  - ⚠️ Не назначена! Нужно назначить")
                else:
                    print("⚠️ Все задачи, блокирующие релиз, сами заблокированы")
                    print("Сначала нужно разблокировать их")
            
            elif blockers.get('blocked_tasks', 0) > 0:
                print("⚠️ Есть заблокированные задачи")
                print("Рекомендую разрешить блокеры:")
                
                blocked_tasks = blockers.get('blocked_tasks', [])
                for blocked in blocked_tasks[:3]:
                    blocking_ids = blocked.get('blocked_by', [])
                    print(f"\n  {blocked['id']}: {blocked['title']}")
                    print(f"  Блокируется: {', '.join(blocking_ids)}")
            
            elif high_tasks:
                task = high_tasks[0]
                print(f"🔥 Следующая задача: {task['id']}: {task['title']}")
                print(f"\n📌 Детали:")
                print(f"  - Приоритет: high")
                print(f"  - Оценка: {task.get('estimate_hours', '?')} часов")
                if task.get('assignee'):
                    print(f"  - Назначена: {task['assignee']}")
                else:
                    print(f"  - Не назначена")
            else:
                print("✅ Нет критических задач!")
                print("Можно взять задачи из backlog или сфокусироваться на качестве:")
                print("  - Написать тесты")
                print("  - Рефакторинг")
                print("  - Документация")
        except Exception as e:
            print(f"✗ Ошибка: {e}")
    
    # ========================================================================
    # Анализ блокеров
    # ========================================================================
    
    def analyze_blockers(self):
        """Анализирует блокеры"""
        print("🔍 Анализирую блокеры...\n")
        
        try:
            resp = requests.get(f"{self.mcp_url}/tasks/blockers/all")
            
            if resp.status_code == 200:
                data = resp.json()
                
                blocked_tasks = data.get('blocked_tasks', [])
                release_blockers = data.get('release_blockers', [])
                
                print("="*60)
                print("🚫 АНАЛИЗ БЛОКЕРОВ")
                print("="*60)
                
                if not blocked_tasks and not release_blockers:
                    print("\n✅ Блокеров нет! Отличная работа!")
                    return
                
                # Заблокированные задачи
                if blocked_tasks:
                    print(f"\n📋 Заблокированные задачи ({len(blocked_tasks)}):\n")
                    for task in blocked_tasks:
                        print(f"  🚫 {task['id']}: {task['title']}")
                        print(f"     Блокируется: {', '.join(task.get('blocked_by', []))}")
                        print(f"     Приоритет: {task['priority']}")
                        print()
                
                # Release blockers
                if release_blockers:
                    print(f"🚀 Задачи, блокирующие релиз ({len(release_blockers)}):\n")
                    for task in release_blockers:
                        status_emoji = {
                            'open': '🔓',
                            'in_progress': '⏳',
                            'waiting_review': '👀'
                        }.get(task['status'], '📋')
                        
                        print(f"  {status_emoji} {task['id']}: {task['title']}")
                        print(f"     Статус: {task['status']}, Приоритет: {task['priority']}")
                        if task.get('assignee'):
                            print(f"     Назначена: {task['assignee']}")
                        else:
                            print(f"     ⚠️ Не назначена!")
                        print()
                
                # Рекомендации
                print("💡 Рекомендации:")
                if release_blockers:
                    actionable = [t for t in release_blockers if t['status'] not in ['blocked', 'done']]
                    if actionable:
                        print(f"  1. Сфокусироваться на {len(actionable)} задач(ах), блокирующих релиз")
                        unassigned = [t for t in actionable if not t.get('assignee')]
                        if unassigned:
                            print(f"  2. Назначить {len(unassigned)} неназначенных задач(и)")
                
                if blocked_tasks:
                    print(f"  3. Разблокировать {len(blocked_tasks)} задач(и)")
            else:
                print(f"✗ Ошибка: {resp.text}")
        except Exception as e:
            print(f"✗ Ошибка: {e}")
