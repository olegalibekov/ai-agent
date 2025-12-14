#!/usr/bin/env python3
"""
Локальный аналитик данных с использованием Ollama LLM
Анализирует CSV, JSON, логи без отправки данных в облако
"""

import json
import csv
import re
from pathlib import Path
from typing import List, Dict, Any
import subprocess


class LocalAnalytics:
    def __init__(self, model_name: str = "llama3.1:8b-instruct-q2_K"):
        """
        Инициализация аналитика
        :param model_name: название модели Ollama для использования
        """
        self.model_name = model_name
        self.data = None
        self.data_summary = None
        
    def load_csv(self, filepath: str) -> None:
        """Загрузка CSV файла"""
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            self.data = list(reader)
        print(f"✓ Загружено {len(self.data)} записей из CSV")
        self._create_summary()
    
    def load_json(self, filepath: str) -> None:
        """Загрузка JSON файла"""
        with open(filepath, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        if isinstance(self.data, dict):
            self.data = [self.data]
        print(f"✓ Загружено {len(self.data)} записей из JSON")
        self._create_summary()
    
    def load_logs(self, filepath: str) -> None:
        """Загрузка лог-файла"""
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Парсинг логов (простой формат)
        self.data = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Пытаемся извлечь уровень логирования и сообщение
            log_pattern = r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+\[(\w+)\]\s+(.*)'
            match = re.match(log_pattern, line)
            
            if match:
                timestamp, level, message = match.groups()
                self.data.append({
                    'timestamp': timestamp,
                    'level': level,
                    'message': message,
                    'raw': line
                })
            else:
                self.data.append({'raw': line})
        
        print(f"✓ Загружено {len(self.data)} записей из логов")
        self._create_summary()
    
    def _create_summary(self) -> None:
        """Создание краткой сводки данных для LLM"""
        if not self.data:
            return
        
        summary = {
            'total_records': len(self.data),
            'sample_records': self.data[:5],  # Первые 5 записей
        }
        
        # Анализ структуры данных
        if self.data:
            first_record = self.data[0]
            if isinstance(first_record, dict):
                summary['fields'] = list(first_record.keys())
                
                # Подсчет уникальных значений для каждого поля
                field_stats = {}
                for field in summary['fields']:
                    values = [str(record.get(field, '')) for record in self.data if record.get(field)]
                    unique_values = set(values)
                    field_stats[field] = {
                        'unique_count': len(unique_values),
                        'sample_values': list(unique_values)[:10]
                    }
                summary['field_statistics'] = field_stats
        
        self.data_summary = summary
    
    def query_ollama(self, prompt: str) -> str:
        """Отправка запроса в Ollama"""
        try:
            result = subprocess.run(
                ['ollama', 'run', self.model_name],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=60
            )
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            return "Ошибка: превышено время ожидания ответа"
        except Exception as e:
            return f"Ошибка: {str(e)}"
    
    def analyze(self, question: str) -> str:
        """
        Анализ данных с помощью LLM
        :param question: вопрос для анализа
        :return: ответ LLM
        """
        if not self.data:
            return "Ошибка: данные не загружены. Используйте load_csv(), load_json() или load_logs()"
        
        # Формируем промпт для LLM
        prompt = f"""Ты - аналитик данных. У тебя есть следующие данные:

Общая информация:
- Всего записей: {self.data_summary['total_records']}
- Поля: {', '.join(self.data_summary.get('fields', []))}

Примеры данных (первые 5 записей):
{json.dumps(self.data_summary['sample_records'], ensure_ascii=False, indent=2)}

Статистика по полям:
{json.dumps(self.data_summary.get('field_statistics', {}), ensure_ascii=False, indent=2)}

Вопрос: {question}

Проанализируй данные и дай краткий, конкретный ответ на вопрос. Если нужно, посчитай статистику по всем данным.
Отвечай на русском языке."""

        print("\n🤖 Анализирую данные...")
        answer = self.query_ollama(prompt)
        return answer
    
    def get_full_data_context(self) -> str:
        """Получить полный контекст данных для сложных запросов"""
        if len(self.data) <= 100:
            # Если данных немного, отправляем все
            return json.dumps(self.data, ensure_ascii=False, indent=2)
        else:
            # Иначе только сводку
            return json.dumps(self.data_summary, ensure_ascii=False, indent=2)


def main():
    """Интерактивный режим работы"""
    import sys
    
    print("=" * 60)
    print("📊 Локальный аналитик данных")
    print("=" * 60)
    
    # Выбор модели
    print("\n🤖 Доступные модели:")
    print("1. llama3.1:8b-instruct-q2_K (быстрая, ~3GB)")
    print("2. llama3.1:8b-instruct-q8_0 (точная, ~8.5GB)")
    print("3. gemma3:4b (компактная, ~3.3GB)")
    
    model_choice = input("\nВыберите модель (1-3, по умолчанию 1): ").strip() or "1"
    models = {
        "1": "llama3.1:8b-instruct-q2_K",
        "2": "llama3.1:8b-instruct-q8_0",
        "3": "gemma3:4b"
    }
    model_name = models.get(model_choice, models["1"])
    
    analytics = LocalAnalytics(model_name=model_name)
    print(f"\n✓ Используется модель: {model_name}")
    
    # Загрузка данных
    print("\n📁 Загрузите файл с данными:")
    filepath = input("Путь к файлу: ").strip()
    
    if not Path(filepath).exists():
        print(f"❌ Файл не найден: {filepath}")
        return
    
    # Определяем тип файла
    ext = Path(filepath).suffix.lower()
    try:
        if ext == '.csv':
            analytics.load_csv(filepath)
        elif ext == '.json':
            analytics.load_json(filepath)
        elif ext in ['.log', '.txt']:
            analytics.load_logs(filepath)
        else:
            print(f"❌ Неподдерживаемый формат файла: {ext}")
            return
    except Exception as e:
        print(f"❌ Ошибка при загрузке файла: {e}")
        return
    
    # Интерактивный режим вопросов
    print("\n" + "=" * 60)
    print("💬 Задавайте вопросы о данных (для выхода: 'exit' или 'quit')")
    print("=" * 60)
    
    while True:
        question = input("\n❓ Ваш вопрос: ").strip()
        
        if question.lower() in ['exit', 'quit', 'выход']:
            print("\n👋 До свидания!")
            break
        
        if not question:
            continue
        
        answer = analytics.analyze(question)
        print(f"\n💡 Ответ:\n{answer}")


if __name__ == "__main__":
    main()
