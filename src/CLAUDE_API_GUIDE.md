# 🔌 Claude API Integration Guide

## Получение API ключа

### 1. Создайте аккаунт на Anthropic Console
1. Перейдите на https://console.anthropic.com/
2. Зарегистрируйтесь или войдите
3. Перейдите в раздел "API Keys"
4. Нажмите "Create Key"
5. Скопируйте ваш API ключ

### 2. Установите API ключ

**Linux/Mac:**
```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

**Windows (PowerShell):**
```powershell
$env:ANTHROPIC_API_KEY='your-api-key-here'
```

**Windows (CMD):**
```cmd
set ANTHROPIC_API_KEY=your-api-key-here
```

**В Python коде:**
```python
import os
os.environ['ANTHROPIC_API_KEY'] = 'your-api-key-here'
```

**Или через .env файл:**
```bash
# Создайте файл .env
echo "ANTHROPIC_API_KEY=your-api-key-here" > .env

# Установите python-dotenv
pip install python-dotenv

# В коде
from dotenv import load_dotenv
load_dotenv()
```

## Доступные модели Claude

### Claude Sonnet 4 (Рекомендуется)
- **Model ID:** `claude-sonnet-4-20250514`
- **Использование:** Лучший баланс скорости и качества
- **Когда использовать:** Большинство задач, ежедневная работа

### Claude Opus 4
- **Model ID:** `claude-opus-4-20250514`
- **Использование:** Самая мощная модель
- **Когда использовать:** Сложные задачи, критически важная точность

### Claude Haiku 4.5
- **Model ID:** `claude-haiku-4-5-20251001`
- **Использование:** Быстрая и экономичная модель
- **Когда использовать:** Простые задачи, большие объёмы

## Базовое использование

### Простой запрос
```python
from personalized_claude_agent import PersonalizedClaudeAgent

agent = PersonalizedClaudeAgent()
response = agent.chat("Explain recursion")
print(response)
```

### С параметрами
```python
response = agent.chat(
    "Write a poem about coding",
    max_tokens=1000,        # Максимум токенов в ответе
    temperature=1.0,        # Креативность (0-1)
    stream=False           # Потоковая передача
)
```

### Потоковые ответы
```python
# Ответ появляется постепенно, как при печати
response = agent.chat(
    "Tell me a long story",
    stream=True
)
```

### Выбор модели
```python
# Sonnet для баланса
agent = PersonalizedClaudeAgent(model="claude-sonnet-4-20250514")

# Opus для сложных задач
agent = PersonalizedClaudeAgent(model="claude-opus-4-20250514")

# Haiku для скорости
agent = PersonalizedClaudeAgent(model="claude-haiku-4-5-20251001")
```

## Параметры API

### max_tokens
Максимальное количество токенов в ответе (примерно 1 токен = 0.75 слова)

```python
response = agent.chat("Explain AI", max_tokens=500)   # Короткий ответ
response = agent.chat("Write essay", max_tokens=4000) # Длинный ответ
```

### temperature
Контролирует креативность (0.0 - 2.0):
- **0.0-0.5:** Более предсказуемо, фактически
- **0.5-1.0:** Сбалансировано (по умолчанию 1.0)
- **1.0-2.0:** Более креативно, разнообразно

```python
# Точный технический ответ
response = agent.chat("Calculate 2+2", temperature=0.0)

# Креативное письмо
response = agent.chat("Write a story", temperature=1.5)
```

### stream
Потоковая передача ответа:

```python
# Без потока - весь ответ сразу
response = agent.chat("Question", stream=False)

# С потоком - ответ появляется постепенно
response = agent.chat("Question", stream=True)
```

## Управление историей разговора

### Просмотр истории
```python
# Получить статистику
stats = agent.get_conversation_summary()
print(stats)
# {'message_count': 6, 'user_messages': 3, 'assistant_messages': 3}
```

### Экспорт разговора
```python
# Сохранить в JSON
agent.export_conversation("my_chat.json")
```

### Сброс истории
```python
# Начать новый разговор
agent.reset_conversation()
```

## Продвинутые возможности

### 1. Автоматическая персонализация

Агент автоматически:
- ✅ Использует ваши предпочтения из конфига
- ✅ Учитывает ваш стек технологий
- ✅ Фокусируется на ваших приоритетах
- ✅ Предлагает ваши любимые пакеты

```python
# Агент знает ваши предпочтения
response = agent.chat("Review my code")
# Автоматически проверит то, что важно для вас
```

### 2. Контекстные подсказки

Агент добавляет контекст автоматически:

```python
# Для code review
agent.chat("Check this function")
# Добавится: [Code review focus: Clean code, No duplication, Performance]

# Для выбора библиотек
agent.chat("What package for HTTP?")
# Добавится: [Preferred packages: requests, httpx, aiohttp]
```

### 3. Умные рекомендации

```python
# Получить персонализированные советы
suggestions = agent.suggest_next_steps("Building REST API")
# Учитывает ваши цели и текущий контекст
```

## Примеры использования

### Code Review
```python
agent = PersonalizedClaudeAgent()

code = """
def calculate_sum(numbers):
    total = 0
    for num in numbers:
        total += num
    return total
"""

response = agent.chat(f"Review this code:\n{code}")
# Агент проверит код с учётом ваших предпочтений
```

### Обучение
```python
# Вопрос по технологии
response = agent.chat("Explain async/await in Python")

# Практический пример
response = agent.chat("Show me how to use decorators")

# Сравнение подходов
response = agent.chat("Compare REST vs GraphQL")
```

### Отладка
```python
error = """
TypeError: unsupported operand type(s) for +: 'int' and 'str'
"""

response = agent.chat(f"Help me fix this error:\n{error}")
```

### Архитектурные вопросы
```python
response = agent.chat(
    "Should I use microservices or monolith for my project?"
)
# Ответ будет учитывать ваш опыт и контекст проекта
```

## Стоимость и лимиты

### Цены (приблизительные)
- **Claude Opus 4:** ~$15 / 1M input tokens, ~$75 / 1M output tokens
- **Claude Sonnet 4:** ~$3 / 1M input tokens, ~$15 / 1M output tokens  
- **Claude Haiku 4.5:** ~$0.80 / 1M input tokens, ~$4 / 1M output tokens

### Лимиты
- **Rate limits:** Зависят от вашего тарифа
- **Max tokens:** До 200K токенов контекста
- **Max output:** До 8K токенов вывода

### Оптимизация затрат

1. **Используйте правильную модель:**
   - Простые задачи → Haiku
   - Большинство задач → Sonnet
   - Сложные задачи → Opus

2. **Контролируйте max_tokens:**
```python
# Короткий ответ дешевле
response = agent.chat("Quick question", max_tokens=500)
```

3. **Очищайте историю:**
```python
# Длинная история = больше токенов
agent.reset_conversation()  # Начать заново
```

## Обработка ошибок

### Базовая обработка
```python
try:
    response = agent.chat("Your question")
except Exception as e:
    print(f"Error: {e}")
```

### Распространённые ошибки

**401 Unauthorized:**
```python
# Проверьте API ключ
if not os.environ.get("ANTHROPIC_API_KEY"):
    print("Set ANTHROPIC_API_KEY")
```

**429 Rate Limit:**
```python
import time

try:
    response = agent.chat("Question")
except Exception as e:
    if "rate_limit" in str(e).lower():
        print("Rate limit reached, waiting...")
        time.sleep(60)  # Подождите минуту
```

**500 Server Error:**
```python
# Повторите запрос
import time

max_retries = 3
for i in range(max_retries):
    try:
        response = agent.chat("Question")
        break
    except Exception as e:
        if i < max_retries - 1:
            time.sleep(2 ** i)  # Exponential backoff
        else:
            raise
```

## Best Practices

### 1. Используйте персонализацию

```python
# ✅ Хорошо - используйте свой конфиг
agent = PersonalizedClaudeAgent(config_path="personalization_config_john_doe.yaml")

# ❌ Плохо - пропускаете персонализацию
agent = PersonalizedClaudeAgent(config_path="personalization_config_john_doe.yaml")
```

### 2. Сохраняйте контекст
```python
# ✅ Хорошо - один агент для всего разговора
agent = PersonalizedClaudeAgent()
agent.chat("Question 1")
agent.chat("Follow-up question")  # Помнит контекст

# ❌ Плохо - новый агент каждый раз
agent1 = PersonalizedClaudeAgent()
agent1.chat("Question 1")
agent2 = PersonalizedClaudeAgent()  # Потерян контекст
agent2.chat("Follow-up")
```

### 3. Выбирайте правильную модель
```python
# ✅ Хорошо
agent_fast = PersonalizedClaudeAgent(model="claude-haiku-4-5-20251001")
agent_fast.chat("Simple question")

agent_powerful = PersonalizedClaudeAgent(model="claude-opus-4-20250514")
agent_powerful.chat("Complex analysis")

# ❌ Плохо - Opus для всего (дорого)
agent = PersonalizedClaudeAgent(model="claude-opus-4-20250514")
agent.chat("What's 2+2?")
```

### 4. Управляйте историей
```python
# ✅ Хорошо
agent = PersonalizedClaudeAgent()

# Работа над задачей 1
agent.chat("Help with task 1")
agent.chat("Follow-up on task 1")

# Переход к задаче 2
agent.reset_conversation()
agent.chat("Help with task 2")

# ❌ Плохо - бесконечная история
agent = PersonalizedClaudeAgent()
for i in range(100):
    agent.chat(f"Question {i}")  # История растёт = дороже
```

## Дополнительная информация

### Документация Anthropic
- API Reference: https://docs.anthropic.com/
- Model comparison: https://docs.anthropic.com/en/docs/models-overview
- Pricing: https://www.anthropic.com/pricing

### Поддержка
- Discord: https://discord.gg/anthropic
- Email: support@anthropic.com

### Альтернативы
Если нужно использовать другие LLM API, можно легко адаптировать:
- OpenAI (GPT-4, GPT-3.5)
- Google (Gemini)
- Mistral AI
- Cohere

Архитектура `PersonalizationManager` не зависит от API и работает с любой LLM.
