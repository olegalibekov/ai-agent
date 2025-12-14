#!/usr/bin/env python3
"""
Тестовый скрипт - работает без Ollama
Показывает как данные загружаются и обрабатываются
"""

from analytics import LocalAnalytics
import json


def test_data_loading():
    """Тест загрузки различных форматов"""
    print("=" * 70)
    print("  ТЕСТ ЗАГРУЗКИ ДАННЫХ")
    print("=" * 70 + "\n")
    
    # Тест CSV
    print("📄 Тест 1: Загрузка CSV")
    print("-" * 70)
    analytics = LocalAnalytics()
    analytics.load_csv("example_errors.csv")
    print(f"\n📊 Структура данных:")
    print(f"  Поля: {analytics.data_summary['fields']}")
    print(f"\n📈 Статистика:")
    for field, stats in analytics.data_summary['field_statistics'].items():
        print(f"  {field}:")
        print(f"    Уникальных значений: {stats['unique_count']}")
        if stats['sample_values']:
            print(f"    Примеры: {', '.join(stats['sample_values'][:3])}")
    
    # Тест JSON
    print("\n\n📄 Тест 2: Загрузка JSON")
    print("-" * 70)
    analytics = LocalAnalytics()
    analytics.load_json("example_sessions.json")
    print(f"\n📊 Структура данных:")
    print(f"  Поля: {analytics.data_summary['fields']}")
    print(f"\n📝 Примеры записей:")
    for i, record in enumerate(analytics.data_summary['sample_records'][:2], 1):
        print(f"\n  Запись {i}:")
        print(f"    ID сессии: {record.get('session_id', 'N/A')}")
        print(f"    Конверсия: {record.get('conversion', 'N/A')}")
        print(f"    Экранов посещено: {len(record.get('screens_visited', []))}")
    
    # Тест логов
    print("\n\n📄 Тест 3: Загрузка логов")
    print("-" * 70)
    analytics = LocalAnalytics()
    analytics.load_logs("example_app.log")
    
    # Подсчет уровней логирования
    level_counts = {}
    for record in analytics.data:
        level = record.get('level', 'UNKNOWN')
        level_counts[level] = level_counts.get(level, 0) + 1
    
    print(f"\n📊 Распределение по уровням:")
    for level, count in sorted(level_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {level}: {count}")
    
    # Самые частые сообщения
    message_counts = {}
    for record in analytics.data:
        msg = record.get('message', '')
        if msg:
            # Берем первые 50 символов для группировки похожих
            msg_key = msg[:50]
            message_counts[msg_key] = message_counts.get(msg_key, 0) + 1
    
    print(f"\n📝 Самые частые сообщения:")
    for msg, count in sorted(message_counts.items(), key=lambda x: x[1], reverse=True)[:3]:
        print(f"  [{count}x] {msg}...")


def show_analysis_examples():
    """Показывает примеры того, что можно узнать из данных"""
    print("\n\n" + "=" * 70)
    print("  ПРИМЕРЫ АНАЛИЗА (без LLM)")
    print("=" * 70 + "\n")
    
    # Анализ CSV
    print("📊 Анализ ошибок (CSV):")
    print("-" * 70)
    analytics = LocalAnalytics()
    analytics.load_csv("example_errors.csv")
    
    error_types = {}
    screen_errors = {}
    severity_counts = {}
    
    for record in analytics.data:
        error_type = record.get('error_type', 'Unknown')
        screen = record.get('screen', 'Unknown')
        severity = record.get('severity', 'Unknown')
        
        error_types[error_type] = error_types.get(error_type, 0) + 1
        screen_errors[screen] = screen_errors.get(screen, 0) + 1
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
    
    print(f"\n🔍 Самые частые ошибки:")
    for error, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:3]:
        print(f"  {error}: {count} раз")
    
    print(f"\n📱 Проблемные экраны:")
    for screen, count in sorted(screen_errors.items(), key=lambda x: x[1], reverse=True)[:3]:
        print(f"  {screen}: {count} ошибок")
    
    print(f"\n⚠️  Критичность:")
    for severity, count in sorted(severity_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {severity}: {count}")
    
    # Анализ JSON
    print("\n\n📱 Анализ сессий (JSON):")
    print("-" * 70)
    analytics = LocalAnalytics()
    analytics.load_json("example_sessions.json")
    
    total_sessions = len(analytics.data)
    conversions = sum(1 for s in analytics.data if s.get('conversion'))
    conversion_rate = (conversions / total_sessions * 100) if total_sessions > 0 else 0
    
    drop_offs = {}
    for session in analytics.data:
        drop_off = session.get('drop_off_screen')
        if drop_off:
            drop_offs[drop_off] = drop_offs.get(drop_off, 0) + 1
    
    print(f"\n📈 Конверсия: {conversions}/{total_sessions} ({conversion_rate:.1f}%)")
    print(f"\n🚪 Где теряются пользователи:")
    for screen, count in sorted(drop_offs.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_sessions * 100)
        print(f"  {screen}: {count} ({percentage:.1f}%)")


def main():
    """Главная функция"""
    print("\n" + "🧪" * 35)
    print("  ТЕСТИРОВАНИЕ СИСТЕМЫ АНАЛИТИКИ")
    print("🧪" * 35 + "\n")
    
    try:
        test_data_loading()
        show_analysis_examples()
        
        print("\n\n" + "=" * 70)
        print("  ✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ")
        print("=" * 70)
        print("\n💡 Для полноценного анализа с LLM запустите:")
        print("   python3 demo.py  - автоматическая демонстрация")
        print("   python3 analytics.py  - интерактивный режим\n")
        
    except FileNotFoundError as e:
        print(f"\n❌ Ошибка: файл не найден - {e}")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")


if __name__ == "__main__":
    main()
