#!/usr/bin/env python3
"""
Расширенный голосовой агент с дополнительными возможностями
"""

import speech_recognition as sr
import anthropic
import os
import time
from typing import Optional, Dict, List
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class AdvancedVoiceAgent:
    """Расширенный голосовой агент с историей и метриками"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Инициализация расширенного агента"""
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
        )
        
        # История диалога
        self.conversation_history: List[Dict] = []
        
        # Метрики
        self.metrics = {
            "queries_processed": 0,
            "recognition_errors": 0,
            "llm_errors": 0,
            "total_tokens_used": 0,
            "start_time": datetime.now()
        }
        
        # Настройка распознавателя
        self.recognizer.energy_threshold = 4000
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        
        print("🎤 Голосовой агент инициализирован")
        self._calibrate_microphone()
    
    def _calibrate_microphone(self):
        """Калибровка микрофона"""
        print("🔧 Калибровка микрофона...")
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            print(f"✅ Калибровка завершена (порог: {self.recognizer.energy_threshold})")
        except Exception as e:
            print(f"⚠️ Ошибка калибровки: {e}")
    
    def listen(self, language: str = 'ru-RU') -> Optional[str]:
        """
        Слушает и распознает речь
        
        Args:
            language: Язык распознавания (по умолчанию русский)
            
        Returns:
            Распознанный текст или None
        """
        print("\n👂 Слушаю... (говорите)")
        
        try:
            with self.microphone as source:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=15)
                print("🔄 Распознаю речь...")
                
                # Пробуем несколько сервисов распознавания
                try:
                    text = self.recognizer.recognize_google(audio, language=language)
                except Exception:
                    # Fallback на английский
                    text = self.recognizer.recognize_google(audio, language='en-US')
                
                print(f"✅ Распознано: '{text}'")
                return text
                
        except sr.WaitTimeoutError:
            print("⏱️ Таймаут ожидания речи")
            self.metrics["recognition_errors"] += 1
            return None
        except sr.UnknownValueError:
            print("❌ Не удалось распознать речь")
            self.metrics["recognition_errors"] += 1
            return None
        except sr.RequestError as e:
            print(f"❌ Ошибка сервиса распознавания: {e}")
            self.metrics["recognition_errors"] += 1
            return None
        except Exception as e:
            print(f"❌ Неожиданная ошибка: {e}")
            self.metrics["recognition_errors"] += 1
            return None
    
    def process_with_llm(self, text: str, use_history: bool = True) -> str:
        """
        Обрабатывает текст через LLM с учетом контекста
        
        Args:
            text: Входной текст
            use_history: Использовать ли историю диалога
            
        Returns:
            Ответ от LLM
        """
        print("🤖 Обрабатываю запрос через LLM...")
        
        try:
            # Формируем сообщения с учетом истории
            messages = []
            
            if use_history and self.conversation_history:
                # Добавляем последние N сообщений из истории
                for entry in self.conversation_history[-3:]:  # Последние 3 обмена
                    messages.append({"role": "user", "content": entry["user"]})
                    messages.append({"role": "assistant", "content": entry["assistant"]})
            
            # Добавляем текущий запрос
            messages.append({"role": "user", "content": text})
            
            # Отправляем запрос
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=messages
            )
            
            answer = response.content[0].text
            
            # Обновляем метрики
            self.metrics["queries_processed"] += 1
            self.metrics["total_tokens_used"] += response.usage.input_tokens + response.usage.output_tokens
            
            # Сохраняем в историю
            self.conversation_history.append({
                "user": text,
                "assistant": answer,
                "timestamp": datetime.now().isoformat(),
                "tokens": {
                    "input": response.usage.input_tokens,
                    "output": response.usage.output_tokens
                }
            })
            
            print(f"✅ Получен ответ (токены: {response.usage.input_tokens}/{response.usage.output_tokens})")
            return answer
            
        except Exception as e:
            print(f"❌ Ошибка при обращении к LLM: {e}")
            self.metrics["llm_errors"] += 1
            return f"Извините, произошла ошибка при обработке запроса: {e}"
    
    def show_metrics(self):
        """Показывает метрики работы агента"""
        runtime = datetime.now() - self.metrics["start_time"]
        
        print("\n" + "="*60)
        print("📊 МЕТРИКИ РАБОТЫ АГЕНТА")
        print("="*60)
        print(f"⏱️ Время работы: {runtime}")
        print(f"✅ Обработано запросов: {self.metrics['queries_processed']}")
        print(f"❌ Ошибок распознавания: {self.metrics['recognition_errors']}")
        print(f"❌ Ошибок LLM: {self.metrics['llm_errors']}")
        print(f"🎯 Использовано токенов: {self.metrics['total_tokens_used']}")
        print(f"💬 Записей в истории: {len(self.conversation_history)}")
        print("="*60 + "\n")
    
    def show_history(self, last_n: int = 5):
        """
        Показывает последние записи из истории диалога
        
        Args:
            last_n: Количество последних записей для показа
        """
        if not self.conversation_history:
            print("📝 История диалога пуста")
            return
        
        print("\n" + "="*60)
        print("📜 ИСТОРИЯ ДИАЛОГА")
        print("="*60)
        
        for i, entry in enumerate(self.conversation_history[-last_n:], 1):
            print(f"\n[{i}] {entry['timestamp']}")
            print(f"👤 User: {entry['user']}")
            print(f"🤖 Assistant: {entry['assistant'][:100]}...")
            print(f"   Токены: {entry['tokens']['input']}/{entry['tokens']['output']}")
        
        print("="*60 + "\n")
    
    def run_single_query(self, language: str = 'ru-RU') -> bool:
        """
        Выполняет один цикл запроса
        
        Args:
            language: Язык распознавания
            
        Returns:
            True для продолжения, False для выхода
        """
        # Слушаем речь
        text = self.listen(language=language)
        
        if text is None:
            return True
        
        # Проверка специальных команд
        text_lower = text.lower()
        
        # Команды выхода
        if any(cmd in text_lower for cmd in ['выход', 'стоп', 'хватит', 'пока', 'выйти']):
            self.show_metrics()
            print("👋 До свидания!")
            return False
        
        # Команда показа метрик
        if 'метрики' in text_lower or 'статистика' in text_lower:
            self.show_metrics()
            return True
        
        # Команда показа истории
        if 'история' in text_lower or 'покажи историю' in text_lower:
            self.show_history()
            return True
        
        # Обрабатываем через LLM
        response = self.process_with_llm(text)
        
        # Выводим ответ
        print("\n" + "="*60)
        print("📝 ОТВЕТ:")
        print(response)
        print("="*60 + "\n")
        
        return True
    
    def run_interactive(self, language: str = 'ru-RU'):
        """
        Запускает агент в интерактивном режиме
        
        Args:
            language: Язык распознавания
        """
        print("\n" + "="*60)
        print("🎙️  РАСШИРЕННЫЙ ГОЛОСОВОЙ АГЕНТ")
        print("="*60)
        print("Команды:")
        print("  - Для выхода: 'выход', 'стоп', 'пока'")
        print("  - Показать метрики: 'метрики', 'статистика'")
        print("  - Показать историю: 'история'")
        print("="*60 + "\n")
        
        try:
            while True:
                if not self.run_single_query(language=language):
                    break
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            print("\n")
            self.show_metrics()
            print("👋 Агент остановлен (Ctrl+C)")


def main():
    """Главная функция"""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("❌ Ошибка: установите переменную окружения ANTHROPIC_API_KEY")
        return
    
    agent = AdvancedVoiceAgent()
    agent.run_interactive()


if __name__ == "__main__":
    main()
