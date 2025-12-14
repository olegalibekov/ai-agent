#!/usr/bin/env python3
"""
Демонстрация возможностей локального аналитика
Автоматически задает вопросы к примерам данных
"""

from analytics import LocalAnalytics
import time


def print_section(title: str):
    """Красивый вывод секции"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def demo_csv_analysis():
    """Демонстрация анализа CSV с ошибками"""
    print_section("📊 АНАЛИЗ CSV: Ошибки приложения")
    
    analytics = LocalAnalytics(model_name="llama3.1:8b-instruct-q2_K")
    analytics.load_csv("example_errors.csv")
    
    questions = [
        "Which error is most common?",
        "Which screen has the most errors?",
        # "Какая ошибка встречается чаще всего?",
        # "На каком экране больше всего ошибок?",
        # "Сколько критических (critical) ошибок?",
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"❓ Вопрос {i}: {question}")
        answer = analytics.analyze(question)
        print(f"💡 Ответ:\n{answer}\n")
        time.sleep(1)


def demo_json_analysis():
    """Демонстрация анализа JSON с сессиями"""
    print_section("📱 АНАЛИЗ JSON: Пользовательские сессии")
    
    analytics = LocalAnalytics(model_name="llama3.1:8b-instruct-q2_K")
    analytics.load_json("example_sessions.json")
    
    questions = [
        # "Где больше всего пользователей теряется (drop_off_screen)?",
        # "Какая конверсия (процент conversion=true)?",
        # "Какой самый частый путь пользователя?",
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"❓ Вопрос {i}: {question}")
        answer = analytics.analyze(question)
        print(f"💡 Ответ:\n{answer}\n")
        time.sleep(1)


def demo_logs_analysis():
    """Демонстрация анализа логов"""
    print_section("📋 АНАЛИЗ ЛОГОВ: Логи приложения")
    
    analytics = LocalAnalytics(model_name="llama3.1:8b-instruct-q2_K")
    analytics.load_logs("example_app.log")
    
    questions = [
        # "Какие ERROR сообщения повторяются чаще всего?",
        # "Есть ли критические проблемы с производительностью?",
        "Are there any critical performance issues?",
        # "Какие проблемы с подключениями?",
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"❓ Вопрос {i}: {question}")
        answer = analytics.analyze(question)
        print(f"💡 Ответ:\n{answer}\n")
        time.sleep(1)


def main():
    """Запуск всех демонстраций"""
    print("⚙️ Используется модель: llama3.1:8b-instruct-q2_K")

    input("Нажмите Enter для начала демонстрации...")
    
    try:
        # CSV анализ
        demo_csv_analysis()
        input("\nНажмите Enter для следующей демонстрации...")
        
        # JSON анализ
        # demo_json_analysis()
        # input("\nНажмите Enter для следующей демонстрации...")
        
        # Анализ логов
        demo_logs_analysis()
        
        print_section("✅ ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА")
        print("Теперь вы можете:")
        print("  1. Запустить интерактивный режим: python3 analytics.py")
        print("  2. Использовать свои данные")
        print("  3. Экспериментировать с разными моделями\n")
        
    except KeyboardInterrupt:
        print("\n\n👋 Демонстрация прервана пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        print("\nУбедитесь что:")
        print("  - Ollama запущен (ollama serve)")
        print("  - Модель загружена (ollama pull llama3.1:8b-instruct-q2_K)")
        print("  - Примеры данных находятся в текущей директории")


if __name__ == "__main__":
    main()
