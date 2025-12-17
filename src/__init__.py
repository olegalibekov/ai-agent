"""
God Agent - Универсальный AI-ассистент
"""

from .god_agent import GodAgent, main
from .voice_module import VoiceInterface
from .rag_engine import RAGEngine
from .mcp_manager import MCPManager
from .memory import MemoryManager
from .task_tracker import TaskTracker, Task, TaskStatus, TaskPriority

__version__ = "1.0.0"
__all__ = [
    "GodAgent",
    "main",
    "VoiceInterface",
    "RAGEngine",
    "MCPManager",
    "MemoryManager",
    "TaskTracker",
    "Task",
    "TaskStatus",
    "TaskPriority",
]
