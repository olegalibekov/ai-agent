"""
MCP Manager для God Agent
Управление MCP серверами и инструментами
"""

import asyncio
import json
from typing import List, Dict, Any, Optional
from pathlib import Path

import httpx


class MCPManager:
    """Менеджер для работы с MCP серверами"""
    
    def __init__(self, config: dict):
        self.config = config
        self.enabled = config.get('enabled', True)
        self.tools_config = config.get('tools', [])
        
        # Инициализированные инструменты
        self.tools = {}
        
        if self.enabled:
            self._initialize_tools()

    def _initialize_tools(self):
        """Инициализация доступных инструментов"""
        for tool_config in self.tools_config:
            if tool_config.get('enabled', False):
                tool_name = tool_config['name']
                config = tool_config.get('config', {})
                self.tools[tool_name] = {
                    'config': config,
                    'handler': self._get_tool_handler(tool_name, config)  # ✅
                }
        
        print(f"🔧 MCP Tools инициализированы: {list(self.tools.keys())}")

    def _get_tool_handler(self, tool_name: str, config: dict):
        """Получение обработчика для инструмента"""
        handlers = {
            'filesystem': FilesystemTool,
            'web_search': WebSearchTool,
            'calendar': CalendarTool,
            'github': GitHubTool,
            'email': EmailTool,
            'slack': SlackTool,
        }

        handler_class = handlers.get(tool_name)
        if handler_class:
            return handler_class(config)  # ✅ Передаем config напрямую

        return None
    
    async def get_tools(self, tool_names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Получение описаний инструментов для Claude API
        
        Args:
            tool_names: Список имен инструментов (None = все)
        
        Returns:
            Список описаний инструментов в формате Claude API
        """
        if not self.enabled:
            return []
        
        tools_to_include = tool_names or list(self.tools.keys())
        
        tool_definitions = []
        for tool_name in tools_to_include:
            if tool_name in self.tools:
                handler = self.tools[tool_name]['handler']
                if handler:
                    tool_definitions.append(handler.get_definition())
        
        return tool_definitions
    
    async def execute_tool(
        self,
        tool_name: str,
        tool_input: Dict[str, Any]
    ) -> str:
        """
        Выполнение инструмента
        
        Args:
            tool_name: Имя инструмента
            tool_input: Входные параметры
        
        Returns:
            Результат выполнения
        """
        if not self.enabled or tool_name not in self.tools:
            return f"Инструмент '{tool_name}' недоступен"
        
        handler = self.tools[tool_name]['handler']
        if not handler:
            return f"Обработчик для '{tool_name}' не найден"
        
        try:
            result = await handler.execute(tool_input)
            return result
        except Exception as e:
            return f"Ошибка выполнения '{tool_name}': {str(e)}"
    
    async def close(self):
        """Закрытие соединений"""
        for tool_name, tool_data in self.tools.items():
            handler = tool_data.get('handler')
            if handler and hasattr(handler, 'close'):
                await handler.close()


# Базовый класс для инструментов
class BaseTool:
    """Базовый класс для всех инструментов"""
    
    def __init__(self, config: dict):
        self.config = config
    
    def get_definition(self) -> Dict[str, Any]:
        """Получение описания инструмента для API"""
        raise NotImplementedError
    
    async def execute(self, input_data: Dict[str, Any]) -> str:
        """Выполнение инструмента"""
        raise NotImplementedError


# Filesystem Tool
class FilesystemTool(BaseTool):
    """Инструмент для работы с файловой системой"""
    
    def get_definition(self) -> Dict[str, Any]:
        return {
            "name": "filesystem",
            "description": "Работа с файлами и директориями: чтение, запись, поиск",
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["read", "write", "list", "search", "delete"],
                        "description": "Действие с файлом"
                    },
                    "path": {
                        "type": "string",
                        "description": "Путь к файлу или директории"
                    },
                    "content": {
                        "type": "string",
                        "description": "Содержимое для записи (для action=write)"
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Паттерн для поиска (для action=search)"
                    }
                },
                "required": ["action", "path"]
            }
        }
    
    async def execute(self, input_data: Dict[str, Any]) -> str:
        action = input_data.get('action')
        path = Path(input_data.get('path', '.'))
        
        # Проверка разрешенных директорий
        allowed_dirs = self.config.get('allowed_directories', [])
        if allowed_dirs:
            if not any(str(path).startswith(d) for d in allowed_dirs):
                return f"Доступ к '{path}' запрещен"
        
        try:
            if action == "read":
                if path.is_file():
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    return f"Содержимое файла {path}:\n\n{content}"
                else:
                    return f"Файл {path} не найден"
            
            elif action == "write":
                content = input_data.get('content', '')
                path.parent.mkdir(parents=True, exist_ok=True)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return f"Файл {path} успешно записан"
            
            elif action == "list":
                if path.is_dir():
                    files = [str(p.relative_to(path)) for p in path.iterdir()]
                    return f"Содержимое {path}:\n" + "\n".join(files)
                else:
                    return f"Директория {path} не найдена"
            
            elif action == "search":
                pattern = input_data.get('pattern', '*')
                results = list(path.rglob(pattern))
                return f"Найдено файлов ({len(results)}):\n" + "\n".join(str(r) for r in results[:20])
            
            elif action == "delete":
                if path.exists():
                    if path.is_file():
                        path.unlink()
                    else:
                        import shutil
                        shutil.rmtree(path)
                    return f"Удалено: {path}"
                else:
                    return f"Не найдено: {path}"
            
            else:
                return f"Неизвестное действие: {action}"
        
        except Exception as e:
            return f"Ошибка: {str(e)}"


# Web Search Tool
class WebSearchTool(BaseTool):
    """Инструмент для поиска в интернете"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.client = httpx.AsyncClient()
    
    def get_definition(self) -> Dict[str, Any]:
        return {
            "name": "web_search",
            "description": "Поиск информации в интернете",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Поисковый запрос"
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "Количество результатов (по умолчанию 5)"
                    }
                },
                "required": ["query"]
            }
        }
    
    async def execute(self, input_data: Dict[str, Any]) -> str:
        query = input_data.get('query', '')
        num_results = input_data.get('num_results', 5)
        
        try:
            # Используем DuckDuckGo API (не требует ключа)
            url = "https://api.duckduckgo.com/"
            params = {
                "q": query,
                "format": "json",
                "no_html": 1
            }
            
            response = await self.client.get(url, params=params)
            data = response.json()
            
            results = []
            
            # Instant Answer
            if data.get('AbstractText'):
                results.append(f"**Краткий ответ:**\n{data['AbstractText']}\n")
            
            # Related Topics
            related = data.get('RelatedTopics', [])[:num_results]
            if related:
                results.append("**Связанные темы:**")
                for topic in related:
                    if isinstance(topic, dict) and topic.get('Text'):
                        results.append(f"- {topic['Text']}")
                        if topic.get('FirstURL'):
                            results.append(f"  Ссылка: {topic['FirstURL']}")
            
            if results:
                return "\n".join(results)
            else:
                return f"По запросу '{query}' ничего не найдено"
        
        except Exception as e:
            return f"Ошибка поиска: {str(e)}"
    
    async def close(self):
        await self.client.aclose()


# Calendar Tool (заглушка)
class CalendarTool(BaseTool):
    """Инструмент для работы с календарем"""
    
    def get_definition(self) -> Dict[str, Any]:
        return {
            "name": "calendar",
            "description": "Управление календарем и событиями",
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list", "add", "delete"],
                        "description": "Действие с календарем"
                    },
                    "title": {
                        "type": "string",
                        "description": "Название события"
                    },
                    "date": {
                        "type": "string",
                        "description": "Дата события (YYYY-MM-DD)"
                    }
                },
                "required": ["action"]
            }
        }
    
    async def execute(self, input_data: Dict[str, Any]) -> str:
        # TODO: Интеграция с Google Calendar API
        return "Календарь: функция в разработке"


# GitHub Tool (заглушка)
class GitHubTool(BaseTool):
    """Инструмент для работы с GitHub"""
    
    def get_definition(self) -> Dict[str, Any]:
        return {
            "name": "github",
            "description": "Работа с GitHub репозиториями, PR, issues",
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list_repos", "list_prs", "create_issue"],
                        "description": "Действие в GitHub"
                    },
                    "repo": {
                        "type": "string",
                        "description": "Название репозитория (owner/repo)"
                    }
                },
                "required": ["action"]
            }
        }
    
    async def execute(self, input_data: Dict[str, Any]) -> str:
        # TODO: Интеграция с GitHub API
        return "GitHub: функция в разработке"


# Email Tool (заглушка)
class EmailTool(BaseTool):
    """Инструмент для работы с email"""
    
    def get_definition(self) -> Dict[str, Any]:
        return {
            "name": "email",
            "description": "Отправка и чтение email",
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["send", "read"],
                        "description": "Действие с email"
                    },
                    "to": {
                        "type": "string",
                        "description": "Адрес получателя"
                    },
                    "subject": {
                        "type": "string",
                        "description": "Тема письма"
                    },
                    "body": {
                        "type": "string",
                        "description": "Текст письма"
                    }
                },
                "required": ["action"]
            }
        }
    
    async def execute(self, input_data: Dict[str, Any]) -> str:
        return "Email: функция в разработке"


# Slack Tool (заглушка)
class SlackTool(BaseTool):
    """Инструмент для работы со Slack"""
    
    def get_definition(self) -> Dict[str, Any]:
        return {
            "name": "slack",
            "description": "Отправка сообщений в Slack",
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["send_message", "read_messages"],
                        "description": "Действие в Slack"
                    },
                    "channel": {
                        "type": "string",
                        "description": "Канал для отправки"
                    },
                    "message": {
                        "type": "string",
                        "description": "Текст сообщения"
                    }
                },
                "required": ["action"]
            }
        }
    
    async def execute(self, input_data: Dict[str, Any]) -> str:
        return "Slack: функция в разработке"
