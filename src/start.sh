#!/bin/bash

# God Agent Quick Start Script

echo "🤖 God Agent - Quick Start"
echo "=========================="
echo ""

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не найден. Установите Python 3.8+"
    exit 1
fi

# Проверка виртуального окружения
if [ ! -d "venv" ]; then
    echo "📦 Создание виртуального окружения..."
    python3 -m venv venv
fi

# Активация
echo "🔄 Активация виртуального окружения..."
source venv/bin/activate

# Проверка зависимостей
if [ ! -f "venv/installed" ]; then
    echo "📥 Установка зависимостей..."
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
    touch venv/installed
fi

# Проверка .env
if [ ! -f ".env" ]; then
    echo "⚠️  .env файл не найден"
    echo "📝 Создаю из .env.example..."
    cp .env.example .env
    echo ""
    echo "❗ ВНИМАНИЕ: Отредактируйте .env и добавьте API ключи!"
    echo "   Минимум нужны: ANTHROPIC_API_KEY и OPENAI_API_KEY"
    echo ""
    read -p "Нажмите Enter после добавления ключей..."
fi

# Создание директорий
echo "📁 Создание необходимых директорий..."
mkdir -p data/vector_store logs workspace documents

# Выбор режима
echo ""
echo "Выберите режим запуска:"
echo "1) Текстовый режим (по умолчанию)"
echo "2) Голосовой режим"
echo "3) Просмотр статистики"
echo "4) Список задач"
echo "5) Информация о системе"
echo ""
read -p "Ваш выбор [1]: " choice
choice=${choice:-1}

case $choice in
    1)
        echo "▶️  Запуск в текстовом режиме..."
        python cli.py start
        ;;
    2)
        echo "▶️  Запуск в голосовом режиме..."
        python cli.py start --mode voice
        ;;
    3)
        echo "📊 Загрузка статистики..."
        python cli.py stats
        ;;
    4)
        echo "✅ Список задач..."
        python cli.py task-list
        ;;
    5)
        echo "ℹ️  Информация о системе..."
        python cli.py info
        ;;
    *)
        echo "❌ Неверный выбор"
        exit 1
        ;;
esac
