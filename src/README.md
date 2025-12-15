# 🤖 Universal AI Agent Personalization

Универсальная система персонализации для AI агента, которая адаптирует ответы под ваш стиль работы, технический стек и контекст. 

**Подходит для любой роли:** ML Engineer, Backend Developer, DevOps, Full-stack, Data Scientist и других.

## 📋 Что включено

1. **personalization_config_john_doe.yaml** - конфигурационный файл с вашим профилем
2. **personalization_manager.py** - менеджер для работы с персонализацией
3. **personalized_claude_agent.py** - интеграция с Claude API (рекомендуется)
4. **simple_example.py** - простой пример использования
5. **demo_standalone.py** - демо без API

## 🎯 Возможности

### Интеграция с Claude API
- ✅ Поддержка всех моделей Claude (Opus, Sonnet, Haiku)
- ✅ Потоковые ответы (stream mode)
- ✅ Управление историей разговора
- ✅ Экспорт диалогов в JSON
- ✅ Гибкая настройка параметров (temperature, max_tokens)

### Адаптация под пользователя
- ✅ Профиль (имя, роль, опыт, образование)
- ✅ Рабочий контекст (текущий проект, архитектура, задачи)
- ✅ Предпочтения в коммуникации
- ✅ Стиль кода и лучшие практики
- ✅ Привычные инструменты и технологии

### Контекстная осведомленность
- ✅ Недавние вызовы и проблемы
- ✅ Текущие проекты
- ✅ Известные болевые точки
- ✅ Цели (краткосрочные, среднесрочные, долгосрочные)

### Умное поведение
- ✅ Проактивные предложения оптимизаций
- ✅ Рекомендации пакетов по контексту
- ✅ Адаптивный стиль ответов
- ✅ Учёт предпочтений в code review

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
pip install anthropic pyyaml
```

### 2. Получите API ключ Claude

1. Зарегистрируйтесь на https://console.anthropic.com/
2. Создайте API ключ в разделе "API Keys"
3. Установите ключ:

```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

**Подробнее:** См. [CLAUDE_API_GUIDE.md](CLAUDE_API_GUIDE.md) для полной инструкции

### 3. Настройка конфига

Скопируйте example конфиг и заполните своими данными:

```bash
cp personalization_config_john_doe.yaml personalization_config_john_doe.yaml
```

Отредактируйте `personalization_config_john_doe.yaml` под себя:

```yaml
user_profile:
  name: "Ваше имя"
  role: "Ваша роль"
  experience:
    primary: "Основной навык"
    secondary: "Дополнительные навыки"
  
work_context:
  current_project: "Название проекта"
  architecture: "Используемая архитектура"
  focus_areas:
    - "Область 1"
    - "Область 2"

preferences:
  communication_style:
    - "Прямой стиль"
    - "Технические детали"
  
  code_style:
    - "Clean code"
    - "Минимум дублирования"
```

**Примечание:** Файл `personalization_config_john_doe.yaml` включён в `.gitignore`, чтобы ваши личные данные не попали в git. В репозитории хранится только `personalization_config.example.yaml` с шаблоном.

### 4. Использование

```python
from personalized_claude_agent import PersonalizedClaudeAgent

# Инициализация
agent = PersonalizedClaudeAgent()

# Просмотр профиля
print(agent.get_profile_summary())

# Общение с агентом
response = agent.chat("Как оптимизировать этот код?")
print(response)

# Потоковый ответ
response = agent.chat("Расскажи историю", stream=True)

# Получить персонализированные рекомендации
suggestions = agent.suggest_next_steps("Работаю над новой фичей")
print(suggestions)
```

**Быстрый старт:** См. [QUICKSTART.md](QUICKSTART.md)
**Подробнее про API:** См. [CLAUDE_API_GUIDE.md](CLAUDE_API_GUIDE.md)

## 🎨 Примеры использования

### Code Review с учётом ваших предпочтений

```python
from personalized_claude_agent import PersonalizedClaudeAgent

agent = PersonalizedClaudeAgent()

code = """
def process_data(items):
  result = []
  for item in items:
    result.append(item * 2)
  return result
"""

response = agent.chat(f"Review this code:\n{code}")
# Агент проверит код с фокусом на ваши предпочтения:
# - Архитектуру и паттерны
# - Дублирование кода
# - Performance
# - Error handling
print(response)
```

### Вопросы по архитектуре

```python
response = agent.chat("Should I use MVC or MVVM for this feature?")
# Агент учтёт вашу текущую архитектуру проекта
# и предложит решение в контексте вашей команды
```

### Помощь с текущими проблемами

```python
response = agent.chat("My app is running slowly with large datasets")
# Агент знает ваши недавние проблемы и технический контекст
# и может предложить решения на основе этой информации
```

## ⚙️ Конфигурация

### Основные секции конфига

#### 1. User Profile
Базовая информация о вас

```yaml
user_profile:
  name: "Your Name"
  role: "Software Developer"
  age: 25
```

#### 2. Work Context
Текущий проект и задачи

```yaml
work_context:
  current_project: "your_app"
  architecture: "Your architecture pattern"
  focus_areas:
    - "Your focus 1"
    - "Your focus 2"
```

#### 3. Preferences
Ваши предпочтения

```yaml
preferences:
  communication_style:
    - "Direct and concise"
  code_style:
    - "Clean code principles"
  tools_and_tech:
    preferred_packages:
      - "package_1"
      - "package_2"
```

#### 4. Response Guidelines
Как агент должен отвечать

```yaml
response_guidelines:
  when_coding:
    - "Provide complete working examples"
    - "Include error handling"
  when_explaining:
    - "Start with practical example"
  avoid:
    - "Overly verbose explanations"
```

#### 5. Context Awareness
Недавний контекст

```yaml
context_awareness:
  recent_challenges:
    - "Your recent challenge"
  ongoing_projects:
    - "Your project"
  known_pain_points:
    - "Your pain point"
```

## 🔧 API Reference

### PersonalizationManager

```python
manager = PersonalizationManager("config.yaml")

# Получить профиль
profile = manager.get_user_profile()

# Получить стиль коммуникации
style = manager.get_communication_style()

# Получить текущий контекст
context = manager.get_current_context()

# Построить system prompt для агента
prompt = manager.build_system_prompt()

# Проверить, нужна ли оптимизация
should_optimize = manager.should_suggest_optimization("nested loops")

# Получить рекомендации пакетов
packages = manager.get_relevant_packages("images")

# Обновить runtime контекст
manager.update_context("last_topic", "BLoC patterns")
```

### PersonalizedAgent

```python
agent = PersonalizedAgent()

# Отправить сообщение
response = agent.chat("Your question here")

# Получить summary профиля
summary = agent.get_profile_summary()

# Предложить следующие шаги
suggestions = agent.suggest_next_steps("Current task")

# Сбросить историю разговора
agent.reset_conversation()
```

## 💡 Расширенные возможности

### 1. Динамическое обновление контекста

```python
agent = PersonalizedAgent()

# Агент автоматически отслеживает темы в разговоре
response = agent.chat("Help with API implementation")
# Контекст обновляется: recent_topics += ['API design']

# Агент автоматически усиливает сообщения контекстом
response = agent.chat("Review my code")
# Добавляется: "[Focus: Clean code, minimal duplication, performance]"
```

### 2. Проактивные предложения

```python
# Агент автоматически предлагает оптимизации
message = "Here's my code with duplicate logic in 3 places"
response = agent.chat(message)
# Агент автоматически включит предложения по рефакторингу
```

### 3. Умные рекомендации пакетов

```python
response = agent.chat("Need to make HTTP requests")
# Агент предложит пакеты из ваших preferred_packages
```

## 🎓 Лучшие практики

### 1. Регулярно обновляйте конфиг
- Добавляйте новые вызовы в `recent_challenges`
- Обновляйте `ongoing_projects`
- Корректируйте предпочтения

### 2. Используйте специфичные термины
```yaml
# ❌ Плохо
focus_areas:
  - "UI"
  - "Code"

# ✅ Хорошо
focus_areas:
  - "Responsive design with CSS Grid"
  - "React component architecture with hooks"
```

### 3. Указывайте конкретные болевые точки
```yaml
known_pain_points:
  - "Memory leaks in WebSocket connections"
  - "Slow database queries on large datasets"
```

### 4. Настройте агента под свой workflow
```yaml
agent_behavior:
  proactivity:
    - "Suggest optimizations when spotting issues"
    - "Point out potential bugs"
```

## 🔍 Примеры кастомизации

### Для ML Engineer

```yaml
user_profile:
  role: "ML Engineer"
  experience:
    primary: "PyTorch, TensorFlow"

preferences:
  communication_style:
    - "Show mathematical intuition"
    - "Include performance metrics"
  
  code_style:
    - "Vectorized operations"
    - "Memory-efficient implementations"

response_guidelines:
  when_coding:
    - "Show shape transformations in comments"
    - "Include training/inference examples"
```

### Для Backend Developer

```yaml
user_profile:
  role: "Backend Developer"
  experience:
    primary: "Python, FastAPI, PostgreSQL"

preferences:
  code_style:
    - "Type hints everywhere"
    - "Comprehensive error handling"
    - "Database transaction safety"

response_guidelines:
  when_coding:
    - "Include API documentation"
    - "Show database migrations"
    - "Consider concurrent access"
```

## 📊 Тестирование

Запустите demo для проверки:

```bash
python personalized_agent_example.py
```

Вы увидите:
- Summary профиля
- Примеры персонализированных ответов
- Тесты контекстной осведомленности
- Рекомендации пакетов

## 🔄 Интеграция в ваш проект

### С существующим чат-ботом

```python
# Ваш существующий бот
class MyBot:
    def __init__(self):
        self.personalization = PersonalizationManager()
        self.system_prompt = self.personalization.build_system_prompt()
    
    def handle_message(self, message):
        # Используйте self.system_prompt в API вызове
        response = self.llm_api.call(
            system=self.system_prompt,
            message=message
        )
        return response
```

### С веб-приложением

```python
from flask import Flask, request, jsonify
from personalized_agent_example import PersonalizedAgent

app = Flask(__name__)
agents = {}  # user_id -> PersonalizedAgent

@app.route('/chat', methods=['POST'])
def chat():
    user_id = request.json['user_id']
    message = request.json['message']
    
    # Получить или создать агента для пользователя
    if user_id not in agents:
        config_path = f"configs/{user_id}.yaml"
        agents[user_id] = PersonalizedAgent(config_path=config_path)
    
    response = agents[user_id].chat(message)
    return jsonify({'response': response})
```

## 🚧 Roadmap

- [ ] Автоматическое обучение на основе истории разговоров
- [ ] Множественные профили (работа/хобби/учёба)
- [ ] Интеграция с календарём для контекста времени
- [ ] Анализ эффективности персонализации
- [ ] Web UI для редактирования конфига
- [ ] Экспорт/импорт профилей

## 📝 Заметки

- API key можно задать через `ANTHROPIC_API_KEY` environment variable
- Конфиг в YAML для удобного редактирования
- Полностью type-safe с помощью dataclasses
- Расширяемая архитектура для новых возможностей

## 🎉 Результат

Теперь у вас есть **персональный AI агент**, который:
- ✅ Знает ваш контекст и предпочтения
- ✅ Адаптирует стиль ответов
- ✅ Даёт релевантные рекомендации
- ✅ Учитывает ваши цели и проекты
- ✅ Проактивно помогает с оптимизациями

Агент станет более полезным, когда вы настроите конфиг под себя!
