"""
Модуль голосового интерфейса для God Agent
Whisper для распознавания речи
"""

import asyncio
import tempfile
from pathlib import Path
from typing import Optional
import wave

import pyaudio
import speech_recognition as sr
from openai import OpenAI


class VoiceInterface:
    """Интерфейс для работы с голосом"""
    
    def __init__(self, config: dict):
        self.config = config
        self.client = OpenAI()
        self.recognizer = sr.Recognizer()
        
        # Настройки аудио
        self.sample_rate = config['input']['sample_rate']
        self.channels = config['input']['channels']
        self.chunk_duration = config['input']['chunk_duration']
        
        # PyAudio для записи
        self.audio = pyaudio.PyAudio()
    
    async def wait_for_wake_word(self, wake_word: str, timeout: int = 30) -> bool:
        """
        Ожидание wake word
        
        Args:
            wake_word: Ключевое слово для активации
            timeout: Таймаут в секундах
        """
        try:
            with sr.Microphone() as source:
                # Калибровка на окружающий шум
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                # Ожидание аудио
                audio = self.recognizer.listen(source, timeout=timeout)
                
                # Распознавание
                text = self.recognizer.recognize_google(
                    audio,
                    language="ru-RU"
                ).lower()
                
                return wake_word.lower() in text
        
        except sr.WaitTimeoutError:
            return False
        except Exception as e:
            print(f"Wake word error: {e}")
            return False
    
    async def record_audio(self, duration: Optional[int] = None) -> Optional[str]:
        """
        Запись аудио с микрофона
        
        Args:
            duration: Длительность записи (None = автоматически по тишине)
        
        Returns:
            Путь к записанному файлу
        """
        try:
            with sr.Microphone(sample_rate=self.sample_rate) as source:
                print("🎤 Слушаю...")
                
                # Калибровка
                self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
                
                # Запись с автоматической остановкой по тишине
                audio = self.recognizer.listen(
                    source,
                    timeout=5,
                    phrase_time_limit=duration or 30
                )
                
                # Сохранение во временный файл
                temp_file = tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=".wav"
                )
                
                with open(temp_file.name, "wb") as f:
                    f.write(audio.get_wav_data())
                
                return temp_file.name
        
        except sr.WaitTimeoutError:
            print("⏱ Тишина слишком долго")
            return None
        except Exception as e:
            print(f"Recording error: {e}")
            return None
    
    async def transcribe(self, audio_path: str) -> str:
        """
        Транскрибация аудио в текст с помощью Whisper
        
        Args:
            audio_path: Путь к аудио файлу
        
        Returns:
            Распознанный текст
        """
        try:
            with open(audio_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model=self.config.get('model', 'whisper-1'),
                    file=audio_file,
                    language=self.config.get('language', 'ru')
                )
            
            # Удаление временного файла
            Path(audio_path).unlink(missing_ok=True)
            
            return transcript.text
        
        except Exception as e:
            print(f"Transcription error: {e}")
            return ""
    
    async def speak(self, text: str, voice: str = "alloy"):
        """
        Озвучивание текста (TTS)
        
        Args:
            text: Текст для озвучивания
            voice: Голос (alloy, echo, fable, onyx, nova, shimmer)
        """
        try:
            response = self.client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text
            )
            
            # Сохранение во временный файл
            temp_file = tempfile.NamedTemporaryFile(
                delete=False,
                suffix=".mp3"
            )
            
            response.stream_to_file(temp_file.name)
            
            # Воспроизведение
            await self._play_audio(temp_file.name)
            
            # Удаление временного файла
            Path(temp_file.name).unlink(missing_ok=True)
        
        except Exception as e:
            print(f"TTS error: {e}")
    
    async def _play_audio(self, audio_path: str):
        """Воспроизведение аудио файла"""
        try:
            # Используем system command для воспроизведения
            # В production лучше использовать библиотеку типа pygame
            import subprocess
            subprocess.run(
                ["ffplay", "-nodisp", "-autoexit", audio_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            print(f"Audio playback error: {e}")
    
    def __del__(self):
        """Очистка ресурсов"""
        if hasattr(self, 'audio'):
            self.audio.terminate()
