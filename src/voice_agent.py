#!/usr/bin/env python3
"""
Голосовой агент: Speech → LLM → Text
День 31 челленджа
"""

import speech_recognition as sr
import anthropic
import os
import time
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class VoiceAgent:
    """Голосовой агент с распознаванием речи и LLM"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Инициализация агента
        
        Args:
            api_key: API ключ Anthropic (если None, берется из переменной окружения)
        """
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Инициализация Anthropic client
        self.client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
        )
        
        # Настройка распознавателя
        self.recognizer.energy_threshold = 4000
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        
        print("🎤 Голосовой агент инициализирован")
        self._calibrate_microphone()
    
    def _calibrate_microphone(self):
        """Калибровка микрофона под окружающий шум"""
        print("🔧 Калибровка микрофона...")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
        print(f"✅ Калибровка завершена (порог: {self.recognizer.energy_threshold})")
    
    def listen(self) -> Optional[str]:
        """
        Слушает и распознает речь
        
        Returns:
            Распознанный текст или None при ошибке
        """
        print("\n👂 Слушаю... (говорите)")
        
        try:
            with self.microphone as source:
                # Слушаем аудио
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                print("🔄 Распознаю речь...")
                
                # Распознаем через Google Speech Recognition
                text = self.recognizer.recognize_google(audio, language='ru-RU')
                print(f"✅ Распознано: '{text}'")
                return text
                
        except sr.WaitTimeoutError:
            print("⏱️ Таймаут ожидания речи")
            return None
        except sr.UnknownValueError:
            print("❌ Не удалось распознать речь")
            return None
        except sr.RequestError as e:
            print(f"❌ Ошибка сервиса распознавания: {e}")
            return None
        except Exception as e:
            print(f"❌ Неожиданная ошибка: {e}")
            return None
    
    def process_with_llm(self, text: str) -> str:
        """
        Обрабатывает текст через LLM
        
        Args:
            text: Входной текст
            
        Returns:
            Ответ от LLM
        """
        print("🤖 Обрабатываю запрос через LLM...")
        
        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": text
                    }
                ]
            )
            
            response = message.content[0].text
            print(f"✅ Получен ответ от LLM")
            return response
            
        except Exception as e:
            print(f"❌ Ошибка при обращении к LLM: {e}")
            return f"Извините, произошла ошибка при обработке запроса: {e}"
    
    def run_single_query(self) -> bool:
        """
        Выполняет один цикл: слушает → обрабатывает → выводит ответ
        
        Returns:
            True если запрос выполнен успешно, False если нужно выйти
        """
        # Слушаем речь
        text = self.listen()
        
        if text is None:
            return True  # Продолжаем работу
        
        # Проверка на команду выхода
        exit_commands = ['выход', 'стоп', 'хватит', 'пока', 'выйти']
        if any(cmd in text.lower() for cmd in exit_commands):
            print("👋 До свидания!")
            return False
        
        # Обрабатываем через LLM
        response = self.process_with_llm(text)
        
        # Выводим ответ
        print("\n" + "="*60)
        print("📝 ОТВЕТ:")
        print(response)
        print("="*60 + "\n")
        
        return True
    
    def run_interactive(self):
        """Запускает агент в интерактивном режиме"""
        print("\n" + "="*60)
        print("🎙️  ГОЛОСОВОЙ АГЕНТ ЗАПУЩЕН")
        print("="*60)
        print("Команды для выхода: 'выход', 'стоп', 'пока'")
        print("="*60 + "\n")
        
        try:
            while True:
                if not self.run_single_query():
                    break
                time.sleep(0.5)  # Небольшая пауза между запросами
                
        except KeyboardInterrupt:
            print("\n\n👋 Агент остановлен (Ctrl+C)")


def main():
    """Главная функция для запуска агента"""
    # Проверяем наличие API ключа
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("❌ Ошибка: установите переменную окружения ANTHROPIC_API_KEY")
        print("Пример: export ANTHROPIC_API_KEY='your-api-key'")
        return
    
    # Создаем и запускаем агента
    agent = VoiceAgent()
    agent.run_interactive()


if __name__ == "__main__":
    main()
