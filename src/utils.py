#!/usr/bin/env python3
"""
Утилиты для настройки и отладки голосового агента
"""

import speech_recognition as sr
import pyaudio
import sys


def list_microphones():
    """Показывает список доступных микрофонов"""
    print("\n" + "="*60)
    print("🎤 ДОСТУПНЫЕ МИКРОФОНЫ")
    print("="*60 + "\n")
    
    try:
        microphones = sr.Microphone.list_microphone_names()
        
        if not microphones:
            print("❌ Микрофоны не найдены")
            return
        
        for i, name in enumerate(microphones):
            print(f"[{i}] {name}")
        
        print("\n💡 Используйте индекс для выбора микрофона:")
        print("   microphone = sr.Microphone(device_index=X)")
        
    except Exception as e:
        print(f"❌ Ошибка при получении списка микрофонов: {e}")


def test_microphone(device_index: int = None):
    """
    Тестирует микрофон
    
    Args:
        device_index: Индекс устройства (None = по умолчанию)
    """
    print("\n" + "="*60)
    print("🔊 ТЕСТ МИКРОФОНА")
    print("="*60 + "\n")
    
    try:
        recognizer = sr.Recognizer()
        
        if device_index is not None:
            mic = sr.Microphone(device_index=device_index)
            print(f"Используется микрофон с индексом: {device_index}")
        else:
            mic = sr.Microphone()
            print("Используется микрофон по умолчанию")
        
        print("\n1️⃣  Калибровка...")
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=2)
        
        print(f"   ✅ Energy threshold: {recognizer.energy_threshold}")
        
        print("\n2️⃣  Говорите что-нибудь...")
        with mic as source:
            audio = recognizer.listen(source, timeout=5)
        
        print("\n3️⃣  Распознавание...")
        
        # Пробуем русский
        try:
            text = recognizer.recognize_google(audio, language='ru-RU')
            print(f"   [RU] ✅ Распознано: '{text}'")
        except:
            print("   [RU] ❌ Не распознано")
        
        # Пробуем английский
        try:
            text = recognizer.recognize_google(audio, language='en-US')
            print(f"   [EN] ✅ Распознано: '{text}'")
        except:
            print("   [EN] ❌ Не распознано")
        
        print("\n✅ Тест завершен")
        
    except sr.WaitTimeoutError:
        print("⏱️ Таймаут - не услышано речи")
    except Exception as e:
        print(f"❌ Ошибка: {e}")


def check_audio_devices():
    """Проверяет аудио устройства через PyAudio"""
    print("\n" + "="*60)
    print("🔌 АУДИО УСТРОЙСТВА (PyAudio)")
    print("="*60 + "\n")
    
    try:
        p = pyaudio.PyAudio()
        
        info = p.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')
        
        print(f"Найдено устройств: {num_devices}\n")
        
        for i in range(num_devices):
            device_info = p.get_device_info_by_host_api_device_index(0, i)
            
            name = device_info.get('name')
            channels = device_info.get('maxInputChannels')
            sample_rate = device_info.get('defaultSampleRate')
            
            device_type = "🎤 INPUT " if channels > 0 else "🔊 OUTPUT"
            
            print(f"[{i}] {device_type}")
            print(f"    Название: {name}")
            print(f"    Каналы: {channels}")
            print(f"    Sample rate: {sample_rate} Hz")
            print()
        
        p.terminate()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")


def check_dependencies():
    """Проверяет установленные зависимости"""
    print("\n" + "="*60)
    print("📦 ПРОВЕРКА ЗАВИСИМОСТЕЙ")
    print("="*60 + "\n")
    
    dependencies = [
        ('speech_recognition', 'SpeechRecognition'),
        ('pyaudio', 'PyAudio'),
        ('anthropic', 'Anthropic API')
    ]
    
    all_ok = True
    
    for module_name, display_name in dependencies:
        try:
            module = __import__(module_name)
            version = getattr(module, '__version__', 'unknown')
            print(f"✅ {display_name}: {version}")
        except ImportError:
            print(f"❌ {display_name}: НЕ УСТАНОВЛЕН")
            all_ok = False
    
    print()
    
    if all_ok:
        print("✅ Все зависимости установлены")
    else:
        print("❌ Некоторые зависимости отсутствуют")
        print("   Установите: pip install -r requirements.txt")


def calibrate_microphone(duration: int = 3):
    """
    Калибрует микрофон и показывает уровень шума
    
    Args:
        duration: Длительность калибровки в секундах
    """
    print("\n" + "="*60)
    print("🔧 КАЛИБРОВКА МИКРОФОНА")
    print("="*60 + "\n")
    
    try:
        recognizer = sr.Recognizer()
        mic = sr.Microphone()
        
        print(f"Калибровка в течение {duration} секунд...")
        print("Пожалуйста, не говорите во время калибровки.\n")
        
        with mic as source:
            # Сохраняем начальное значение
            initial_threshold = recognizer.energy_threshold
            
            # Калибруем
            recognizer.adjust_for_ambient_noise(source, duration=duration)
            
            # Новое значение
            final_threshold = recognizer.energy_threshold
        
        print("✅ Калибровка завершена\n")
        print(f"Начальный порог:   {initial_threshold}")
        print(f"Откалиброванный:   {final_threshold}")
        print(f"Изменение:         {final_threshold - initial_threshold:+.0f}")
        
        # Рекомендации
        print("\n💡 Рекомендации:")
        if final_threshold < 2000:
            print("   • Очень тихая среда - отлично!")
        elif final_threshold < 4000:
            print("   • Нормальный уровень шума")
        elif final_threshold < 6000:
            print("   • Повышенный шум - проверьте окружение")
        else:
            print("   • Высокий уровень шума - рекомендуется найти более тихое место")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")


def show_usage():
    """Показывает инструкции по использованию"""
    print("\n" + "="*60)
    print("📖 УТИЛИТЫ ДЛЯ ГОЛОСОВОГО АГЕНТА")
    print("="*60 + "\n")
    print("Использование:")
    print("  python utils.py list           # Список микрофонов")
    print("  python utils.py test [index]   # Тест микрофона")
    print("  python utils.py devices        # Аудио устройства")
    print("  python utils.py deps           # Проверка зависимостей")
    print("  python utils.py calibrate [s]  # Калибровка микрофона")
    print("  python utils.py all            # Все проверки")
    print("\nПримеры:")
    print("  python utils.py test 0         # Тест микрофона #0")
    print("  python utils.py calibrate 5    # Калибровка 5 секунд")
    print()


def run_all_checks():
    """Запускает все проверки"""
    check_dependencies()
    list_microphones()
    check_audio_devices()
    calibrate_microphone()
    
    print("\n" + "="*60)
    print("✅ ВСЕ ПРОВЕРКИ ЗАВЕРШЕНЫ")
    print("="*60 + "\n")
    print("Теперь вы можете запустить:")
    print("  python voice_agent.py")
    print()


def main():
    """Главная функция"""
    if len(sys.argv) < 2:
        show_usage()
        return
    
    command = sys.argv[1].lower()
    
    if command == 'list':
        list_microphones()
    
    elif command == 'test':
        device_index = None
        if len(sys.argv) > 2:
            try:
                device_index = int(sys.argv[2])
            except ValueError:
                print("❌ Индекс должен быть числом")
                return
        test_microphone(device_index)
    
    elif command == 'devices':
        check_audio_devices()
    
    elif command == 'deps':
        check_dependencies()
    
    elif command == 'calibrate':
        duration = 3
        if len(sys.argv) > 2:
            try:
                duration = int(sys.argv[2])
            except ValueError:
                print("❌ Длительность должна быть числом")
                return
        calibrate_microphone(duration)
    
    elif command == 'all':
        run_all_checks()
    
    else:
        print(f"❌ Неизвестная команда: {command}")
        show_usage()


if __name__ == "__main__":
    main()
