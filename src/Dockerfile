FROM python:3.11-slim

# Метаданные
LABEL maintainer="Oleg <oleg@example.com>"
LABEL description="God Agent - Universal AI Assistant"
LABEL version="1.0.0"

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    portaudio19-dev \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Копирование requirements
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование приложения
COPY . .

# Создание директорий
RUN mkdir -p data/vector_store logs workspace documents

# Переменные окружения
ENV PYTHONUNBUFFERED=1
ENV ANTHROPIC_API_KEY=""
ENV OPENAI_API_KEY=""

# Точка входа
ENTRYPOINT ["python", "cli.py"]

# По умолчанию - текстовый режим
CMD ["start"]
