"""
Примеры использования God Agent
"""

import asyncio
from god_agent import GodAgent


async def example_1_basic_conversation():
    """Пример 1: Базовый разговор"""
    print("\n=== Пример 1: Базовый разговор ===\n")
    
    agent = GodAgent()
    
    # Простой вопрос
    response = await agent.process_input(
        "Привет! Что ты умеешь?"
    )
    print(f"Agent: {response}\n")
    
    # Вопрос с контекстом
    response = await agent.process_input(
        "Помоги мне организовать задачи на сегодня"
    )
    print(f"Agent: {response}\n")
    
    await agent.shutdown()


async def example_2_file_operations():
    """Пример 2: Работа с файлами"""
    print("\n=== Пример 2: Работа с файлами ===\n")
    
    agent = GodAgent()
    
    # Поиск файлов
    response = await agent.process_input(
        "Найди все Python файлы в текущей директории"
    )
    print(f"Agent: {response}\n")
    
    # Чтение файла
    response = await agent.process_input(
        "Прочитай файл config.yaml и расскажи что там"
    )
    print(f"Agent: {response}\n")
    
    await agent.shutdown()


async def example_3_web_search():
    """Пример 3: Поиск в интернете"""
    print("\n=== Пример 3: Веб-поиск ===\n")
    
    agent = GodAgent()
    
    # Поиск информации
    response = await agent.process_input(
        "Найди последние новости про Flutter 3.19"
    )
    print(f"Agent: {response}\n")
    
    # Поиск с анализом
    response = await agent.process_input(
        "Что изменилось в новой версии Claude API?"
    )
    print(f"Agent: {response}\n")
    
    await agent.shutdown()


async def example_4_task_management():
    """Пример 4: Управление задачами"""
    print("\n=== Пример 4: Управление задачами ===\n")
    
    agent = GodAgent()
    
    # Создание задачи
    response = await agent.process_input(
        "Создай задачу: Код-ревью PR #123, высокий приоритет, срок завтра"
    )
    print(f"Agent: {response}\n")
    
    # Список задач
    response = await agent.process_input(
        "Покажи мои активные задачи"
    )
    print(f"Agent: {response}\n")
    
    # Анализ
    response = await agent.process_input(
        "Какие задачи у меня просрочены?"
    )
    print(f"Agent: {response}\n")
    
    await agent.shutdown()


async def example_5_context_memory():
    """Пример 5: Работа с контекстом и памятью"""
    print("\n=== Пример 5: Контекст и память ===\n")
    
    agent = GodAgent()
    
    # Сохранение информации
    response = await agent.process_input(
        "Запомни: я работаю над Flutter приложением для финтеха"
    )
    print(f"Agent: {response}\n")
    
    # Использование контекста
    response = await agent.process_input(
        "Какие лучшие практики безопасности для моего проекта?"
    )
    print(f"Agent: {response}\n")
    
    # Отсылка к прошлому
    response = await agent.process_input(
        "Что мы обсуждали про мой проект?"
    )
    print(f"Agent: {response}\n")
    
    await agent.shutdown()


async def example_6_complex_workflow():
    """Пример 6: Комплексный workflow"""
    print("\n=== Пример 6: Комплексный workflow ===\n")
    
    agent = GodAgent()
    
    # Многошаговая задача
    steps = [
        "Найди информацию про state management в Flutter",
        "Сравни BLoC и Riverpod",
        "Создай задачу: Изучить документацию по выбранному решению",
        "Добавь заметку в память: Планирую использовать Riverpod"
    ]
    
    for i, step in enumerate(steps, 1):
        print(f"\n--- Шаг {i}: {step} ---")
        response = await agent.process_input(step)
        print(f"Agent: {response}\n")
    
    await agent.shutdown()


async def example_7_rag_search():
    """Пример 7: Поиск в базе знаний"""
    print("\n=== Пример 7: RAG поиск ===\n")
    
    agent = GodAgent()
    
    # Добавление документов в RAG
    documents = [
        {
            'text': 'Flutter - это UI фреймворк от Google для создания кроссплатформенных приложений',
            'metadata': {'type': 'note', 'topic': 'flutter'}
        },
        {
            'text': 'BLoC (Business Logic Component) - паттерн управления состоянием в Flutter',
            'metadata': {'type': 'note', 'topic': 'state_management'}
        },
        {
            'text': 'Riverpod - современная альтернатива Provider для управления состоянием',
            'metadata': {'type': 'note', 'topic': 'state_management'}
        }
    ]
    
    print("Добавление документов в базу знаний...")
    await agent.rag.add_documents(documents)
    
    # Поиск по базе знаний
    response = await agent.process_input(
        "Что ты знаешь про управление состоянием во Flutter?"
    )
    print(f"Agent: {response}\n")
    
    await agent.shutdown()


async def example_8_proactive_suggestions():
    """Пример 8: Проактивные предложения"""
    print("\n=== Пример 8: Проактивные предложения ===\n")
    
    agent = GodAgent()
    
    # Контекст для проактивности
    response = await agent.process_input(
        "Я работаю над новым Flutter проектом. Нужно настроить CI/CD"
    )
    print(f"Agent: {response}\n")
    
    # Агент должен предложить следующие шаги
    response = await agent.process_input(
        "Что мне делать дальше?"
    )
    print(f"Agent: {response}\n")
    
    await agent.shutdown()


async def run_all_examples():
    """Запуск всех примеров"""
    examples = [
        example_1_basic_conversation,
        example_2_file_operations,
        example_3_web_search,
        example_4_task_management,
        example_5_context_memory,
        example_6_complex_workflow,
        example_7_rag_search,
        example_8_proactive_suggestions,
    ]
    
    for example in examples:
        try:
            await example()
            await asyncio.sleep(1)  # Пауза между примерами
        except Exception as e:
            print(f"Ошибка в {example.__name__}: {e}")
            continue


if __name__ == "__main__":
    print("=" * 60)
    print("God Agent - Примеры использования")
    print("=" * 60)
    
    # Выбор примера
    print("\nВыберите пример:")
    print("0 - Запустить все примеры")
    print("1 - Базовый разговор")
    print("2 - Работа с файлами")
    print("3 - Веб-поиск")
    print("4 - Управление задачами")
    print("5 - Контекст и память")
    print("6 - Комплексный workflow")
    print("7 - RAG поиск")
    print("8 - Проактивные предложения")
    
    try:
        choice = int(input("\nВаш выбор: "))
        
        if choice == 0:
            asyncio.run(run_all_examples())
        elif 1 <= choice <= 8:
            examples = [
                example_1_basic_conversation,
                example_2_file_operations,
                example_3_web_search,
                example_4_task_management,
                example_5_context_memory,
                example_6_complex_workflow,
                example_7_rag_search,
                example_8_proactive_suggestions,
            ]
            asyncio.run(examples[choice - 1]())
        else:
            print("Неверный выбор")
    
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем")
    except Exception as e:
        print(f"\nОшибка: {e}")
