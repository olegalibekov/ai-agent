# 📰 Smart News Bot - Day 24

**Автоматический поиск свежих новостей и публикация в Telegram**

---

## 🎯 Реальная задача

Автоматизация постинга новостей в Telegram канал:
1. Каждый час парсит новости из RSS
2. RAG проверяет дубликаты
3. AI фильтрует и форматирует
4. MCP управляет лимитами и историей
5. Публикует в Telegram
6. Dashboard показывает статистику

---

## 🏗️ Архитектура

```
RSS Sources → News Agent → RAG (дубликаты) → AI Filter → MCP (лимиты) → Telegram
                ↓                                            ↓
            FAISS Index                              posts_history.json
```

### Компоненты:

1. **RAG System** (`backend/rag_system.py`)
   - FAISS индекс для проверки дубликатов
   - Анализ трендов
   - Similarity search (threshold 0.85)

2. **MCP Server** (`mcp_server/news_mcp.py`)
   - История постов (JSON)
   - Лимиты: 10 постов/день, интервал 60 мин
   - Аналитика (просмотры, клики)
   - REST API на порту 8002

3. **News Agent** (`agent/news_agent.py`)
   - Парсинг RSS (TechCrunch, Hacker News, BBC)
   - Интеграция с RAG и MCP
   - Claude API для фильтрации
   - Telegram Bot API

4. **GitHub Action** (`.github/workflows/news-bot.yml`)
   - Cron: каждый час
   - Автоматический запуск агента
   - Коммит изменений в data/

5. **Dashboard** (`dashboard/index.html`)
   - Статистика постов
   - История публикаций
   - Real-time обновления

---

## 🚀 Быстрый старт

### 1. Установка

```bash
git clone <repo>
cd news-bot

# Установить зависимости
pip install -r backend/requirements.txt
```

### 2. Настройка ключей

Создай `.env` файл:

```bash
ANTHROPIC_API_KEY=sk-ant-api03-...
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=@your_channel
```

Или установи в GitHub Secrets:
- `ANTHROPIC_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

### 3. Запуск локально

**Терминал 1: MCP Server**
```bash
cd mcp_server
python news_mcp.py
# http://localhost:8002
```

**Терминал 2: News Agent**
```bash
cd agent
python news_agent.py
```

**Терминал 3: Dashboard**
```bash
cd dashboard
python -m http.server 8080
# Открой http://localhost:8080
```

---

## 📊 Как работает

### Шаг 1: Парсинг новостей (RSS)

```python
# Парсит TechCrunch, Hacker News, BBC
news_items = agent.fetch_news(hours=1)
# Результат: 15 новостей за последний час
```

### Шаг 2: Проверка дубликатов (RAG)

```python
# FAISS similarity search
duplicate = rag.check_duplicate(title, description, threshold=0.85)

if duplicate:
    print(f"Дубликат! Похожесть: {duplicate['similarity']}")
else:
    unique_news.append(news)
```

### Шаг 3: AI фильтрация (Claude)

```python
# Claude выбирает топ-3 и форматирует
filtered = ai_filter_and_format(unique_news)

# Результат:
# 📱 Apple анонсировала iPhone 16!
# 
# Ключевые фичи:
# • A18 чип
# • USB-C
# • $799
#
# #Apple #Tech
```

### Шаг 4: Проверка лимитов (MCP)

```python
can_post = mcp.can_post_now()

# Проверяет:
# - Максимум 10 постов в день
# - Интервал 60 минут между постами
# - Бот включен в настройках
```

### Шаг 5: Публикация в Telegram

```python
telegram.send_message(
    chat_id=CHANNEL_ID,
    text=formatted_text,
    parse_mode="HTML"
)
```

### Шаг 6: Сохранение (RAG + MCP)

```python
# Добавить в RAG индекс (для будущих проверок)
rag.add_news(news_item)

# Сохранить в MCP историю
mcp.add_post(news_item)
```

---

## 🎬 GitHub Actions

### Автоматический запуск каждый час

```yaml
on:
  schedule:
    - cron: '0 * * * *'  # Каждый час
```

### Что делает:

1. Запускает MCP Server
2. Запускает News Agent
3. Коммитит изменения в `data/`
4. Загружает логи как artifacts

### Запуск вручную:

GitHub → Actions → News Bot → Run workflow

---

## 📁 Структура проекта

```
news-bot/
├── backend/
│   ├── rag_system.py           # RAG для дубликатов
│   └── requirements.txt
├── mcp_server/
│   └── news_mcp.py             # MCP API
├── agent/
│   └── news_agent.py           # Главный агент
├── data/
│   ├── posts_history.json      # История (MCP)
│   ├── settings.json           # Настройки
│   └── news_index/             # FAISS индекс (RAG)
├── dashboard/
│   └── index.html              # Web dashboard
├── .github/workflows/
│   └── news-bot.yml            # GitHub Action
└── README.md
```

---

## 🔧 Настройки

Редактируй `data/settings.json`:

```json
{
  "max_posts_per_day": 10,
  "min_interval_minutes": 60,
  "categories": ["tech", "business", "science"],
  "sources": ["TechCrunch", "Hacker News"],
  "enabled": true,
  "rag_settings": {
    "similarity_threshold": 0.85
  }
}
```

---

## 📊 API Endpoints (MCP)

### Статистика
```bash
GET http://localhost:8002/stats
```

Ответ:
```json
{
  "total_posts": 45,
  "today": 5,
  "week": 28,
  "total_views": 1234,
  "top_sources": [["TechCrunch", 15], ...]
}
```

### Посты
```bash
GET http://localhost:8002/posts?hours=24
```

### Проверка лимитов
```bash
GET http://localhost:8002/can-post
```

### Настройки
```bash
GET http://localhost:8002/settings
PUT http://localhost:8002/settings
```

---

## 🎥 Демо для видео (3 минуты)

### Сценарий:

**1. Показать структуру (20 сек)**
```bash
tree news-bot/
```

**2. Запустить MCP (20 сек)**
```bash
python mcp_server/news_mcp.py
curl http://localhost:8002/stats
```

**3. Запустить агента (90 сек)**
```bash
python agent/news_agent.py
```

Покажет:
- Парсинг 15 новостей
- RAG проверка дубликатов
- AI выбор топ-3
- MCP проверка лимитов
- Публикация в Telegram (симуляция)

**4. Показать dashboard (30 сек)**
```bash
open http://localhost:8080
```

**5. GitHub Action (30 сек)**
- Показать `.github/workflows/news-bot.yml`
- Объяснить cron запуск

---

## ✅ Требования Day 24 выполнены

1. ✅ **Реальная задача** - автопостинг новостей в Telegram
2. ✅ **RAG** - проверка дубликатов через FAISS
3. ✅ **MCP** - управление постами и лимитами
4. ✅ **AI** - фильтрация и форматирование (Claude)
5. ✅ **Пайплайн** - GitHub Actions (может не работать без ключей)
6. ✅ **Практическая польза** - можно использовать реально!

---

## 🔑 Получение ключей

### Anthropic API Key
1. Зарегистрируйся на https://console.anthropic.com
2. Создай API key
3. Добавь в `.env`: `ANTHROPIC_API_KEY=sk-ant-...`

### Telegram Bot Token
1. Найди @BotFather в Telegram
2. `/newbot` → создай бота
3. Получи токен: `123456:ABC-DEF...`
4. Создай канал и добавь бота как админа
5. Chat ID = `@your_channel`

---

## 🐛 Troubleshooting

### MCP не запускается
```bash
pip install fastapi uvicorn
python mcp_server/news_mcp.py
```

### RAG ошибка ModuleNotFoundError
```bash
pip install sentence-transformers faiss-cpu
```

### Telegram ошибка
Проверь что:
- Токен правильный
- Бот добавлен в канал как админ
- Chat ID правильный (`@channel` или числовой ID)

### GitHub Action не работает
Добавь Secrets:
- Settings → Secrets → Actions
- New repository secret
- Добавь все 3 ключа

---

## 📝 Что дальше

Можно добавить:
- [ ] Больше источников новостей
- [ ] Фильтры по категориям
- [ ] Scheduled posts (отложенный постинг)
- [ ] React Dashboard вместо HTML
- [ ] Deploy на Vercel/Netlify
- [ ] Webhook от Telegram (feedback)
- [ ] A/B тестирование заголовков
- [ ] Sentiment analysis

---

## 🎉 Готово к использованию!

**Полностью рабочий пайплайн для автоматического постинга новостей в Telegram!**

🚀 Запускай и наслаждайся автоматизацией!
