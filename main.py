#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from dataclasses import dataclass, field
from typing import List, Dict, Any

from dotenv import load_dotenv
from openai import OpenAI

# ===================== МОДЕЛИ =====================
MODEL_MAIN = "gpt-5"          # если нет доступа → "gpt-4.1"
MODEL_SUMMARY = "gpt-5-mini"  # если нет доступа → "gpt-4.1-mini"
MODEL_JUDGE = "gpt-5-mini"    # «судья» для сравнения

# ===================== INIT =====================

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY not found")

print(f"[INIT] API OK: {api_key[:7]}***")

client = OpenAI()

# ===================== БАЗОВАЯ СЕССИЯ =====================

@dataclass
class BaseChatSession:
    model: str = MODEL_MAIN
    system_prompt: str = "Ты полезный ассистент."
    messages: List[Dict[str, Any]] = field(default_factory=list)
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0

    def __post_init__(self):
        self.messages.append({"role": "system", "content": self.system_prompt})

    def _register_usage(self, r):
        """
        Для Responses API:
        r.usage.input_tokens  -> prompt
        r.usage.output_tokens -> completion
        """
        if r.usage:
            self.total_prompt_tokens += r.usage.input_tokens
            self.total_completion_tokens += r.usage.output_tokens

    def _chat_raw(self) -> str:
        r = client.responses.create(
            model=self.model,
            input=self.messages,
        )
        self._register_usage(r)
        return r.output_text

    def chat(self, user_msg: str) -> str:
        """Обычный шаг диалога."""
        self.messages.append({"role": "user", "content": user_msg})
        ans = self._chat_raw()
        self.messages.append({"role": "assistant", "content": ans})
        return ans


@dataclass
class SimpleChatSession(BaseChatSession):
    """Сессия без сжатия истории."""
    pass


# ===================== СЕССИЯ СО СЖАТИЕМ =====================

@dataclass
class CompressedChatSession(BaseChatSession):
    """
    Сессия с периодическим сжатием истории:
    - каждые compact_every_n_turns ответов ассистента
      сжимаем середину в одно system-сообщение "Summary: ...".
    """

    summary_model: str = MODEL_SUMMARY
    compact_every_n_turns: int = 4
    keep_last_messages: int = 4
    turns_count: int = 0

    def chat(self, user_msg: str) -> str:
        self.messages.append({"role": "user", "content": user_msg})

        r = client.responses.create(
            model=self.model,
            input=self.messages,
        )
        self._register_usage(r)

        ans = r.output_text
        self.messages.append({"role": "assistant", "content": ans})
        self.turns_count += 1

        # периодически сжимаем историю
        if self.turns_count % self.compact_every_n_turns == 0:
            print("[COMPRESS] Running compression…")
            self._compact()

        return ans

    def _compact(self):
        """
        Простая стратегия:
        - prefix: только первое system-сообщение
        - middle: всё между prefix и хвостом (keep_last_messages)
        - tail: последние keep_last_messages сообщений
        - middle -> summary (через модель summary_model)
        - messages = prefix + [summary] + tail
        """
        if len(self.messages) <= self.keep_last_messages + 1:
            return

        prefix = [self.messages[0]]  # system
        middle = self.messages[1:-self.keep_last_messages]
        tail = self.messages[-self.keep_last_messages:]

        if len(middle) < 2:
            return

        summary = self._summarize(middle)
        summary_msg = {"role": "system", "content": "Summary:\n" + summary}
        self.messages = prefix + [summary_msg] + tail

    def _summarize(self, msgs: List[Dict[str, Any]]) -> str:
        text = "\n".join([f"{m['role']}: {m['content']}" for m in msgs])

        r = client.responses.create(
            model=self.summary_model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Сделай сжатое, фактическое резюме диалога. "
                        "Не добавляй новую информацию, только перескажи суть."
                    ),
                },
                {"role": "user", "content": text},
            ],
        )
        self._register_usage(r)
        return r.output_text


# ===================== УТИЛИТЫ =====================

def run_script(session: BaseChatSession, script: List[str]) -> List[str]:
    answers = []
    for i, msg in enumerate(script, 1):
        print(f"\n=== {session.__class__.__name__} | USER {i} ===")
        print(msg)
        ans = session.chat(msg)
        print(f"--- BOT {i} ---")
        print(ans)
        answers.append(ans)
    return answers


def print_stats(label: str, s: BaseChatSession):
    total = s.total_prompt_tokens + s.total_completion_tokens
    print(f"\n===== {label} =====")
    print("Prompt tokens:    ", s.total_prompt_tokens)
    print("Completion tokens:", s.total_completion_tokens)
    print("Total tokens:     ", total)


def format_dialog_for_analysis(session: BaseChatSession, label: str) -> str:
    """
    Превращаем messages в читаемый текст для судьи:
    system / user / assistant, по шагам.
    """
    lines: List[str] = [f"=== {label} ==="]
    for i, m in enumerate(session.messages):
        role = m["role"]
        content = str(m["content"])
        lines.append(f"{i:02d} [{role}]: {content}")
    return "\n".join(lines)


def compare_sessions_with_judge(
    simple: BaseChatSession,
    compressed: BaseChatSession,
    simple_final: str,
    compressed_final: str,
) -> str:
    """
    Дополнительный финальный запрос (meta-prompt), который сравнивает:
    - как продолжается разговор с полной историей vs summary
    - качество ответов
    - использование токенов
    """
    simple_dialog = format_dialog_for_analysis(simple, "SIMPLE (без сжатия)")
    compressed_dialog = format_dialog_for_analysis(compressed, "COMPRESSED (со сжатием)")

    simple_total = simple.total_prompt_tokens + simple.total_completion_tokens
    compressed_total = compressed.total_prompt_tokens + compressed.total_completion_tokens

    judge_prompt = f"""
У тебя есть два диалога с пользователем, смоделированных двумя агентами:

1) SIMPLE — агент, который всегда видит полную историю без сжатия.
2) COMPRESSED — агент, который периодически сжимает историю в summary и опирается на это summary.

Ниже даны обе истории в текстовом виде, включая финальный вопрос и финальный ответ каждого агента.

----- SIMPLE DIALOG -----
{simple_dialog}

----- COMPRESSED DIALOG -----
{compressed_dialog}

Статистика токенов:
- SIMPLE: prompt={simple.total_prompt_tokens}, completion={simple.total_completion_tokens}, total={simple_total}
- COMPRESSED: prompt={compressed.total_prompt_tokens}, completion={compressed.total_completion_tokens}, total={compressed_total}

Требуется:

1) Кратко сравни, как оба агента продолжают финальный разговор
   с учётом их «памяти» (полная история vs summary).
   Отметь, теряет ли compressed-агент важные детали или нет.

2) Оцени качество финальных ответов:
   - укажи, различаются ли смысл и полнота;
   - где ответ точнее/яснее/полезнее;
   - есть ли заметные искажения из-за сжатия.

3) Сопоставь это с использованием токенов:
   - кто потратил больше токенов и за счёт чего;
   - есть ли потенциальный выигрыш от компрессии в более длинных диалогах.

Отвечай структурированно, по пунктам 1–3. Пиши кратко, но по делу.
"""

    r = client.responses.create(
        model=MODEL_JUDGE,
        input=[
            {"role": "system", "content": "Ты аккуратный и строгий аналитик качества диалогов ИИ."},
            {"role": "user", "content": judge_prompt},
        ],
    )
    return r.output_text


# ===================== MAIN =====================

def main():
    print("== START ==")

    script = [
        "Привет! Как дела?",
        "Что умеет этот бот?",
        "Дай пример простой функции на Python.",
        "Как работает цикл for?",
        "Что такое список?",
        "Приведи пример списка из трёх элементов.",
        "Что такое словарь?",
        "Подытожь всё коротко.",
    ]

    final_query = (
        "Теперь, опираясь на весь наш предыдущий диалог, "
        "кратко опиши, чему я учился и что ты мне объяснял."
    )

    # 1. Обычная сессия
    simple = SimpleChatSession(
        model=MODEL_MAIN,
        system_prompt="Ты помогаешь новичку разбираться в Python и объясняешь просто.",
    )

    # 2. Сжатая сессия
    compressed = CompressedChatSession(
        model=MODEL_MAIN,
        summary_model=MODEL_SUMMARY,
        compact_every_n_turns=4,    # для демо — часто
        keep_last_messages=4,
        system_prompt="Ты помогаешь новичку разбираться в Python и объясняешь просто.",
    )

    print("\n*** SIMPLE SESSION ***")
    _ = run_script(simple, script)

    print("\n*** COMPRESSED SESSION ***")
    _ = run_script(compressed, script)

    # Финальный вопрос к обеим сессиям
    print("\n=== FINAL QUESTION (SIMPLE) ===")
    simple_final = simple.chat(final_query)
    print(simple_final)

    print("\n=== FINAL QUESTION (COMPRESSED) ===")
    compressed_final = compressed.chat(final_query)
    print(compressed_final)

    # Статы
    print_stats("Без сжатия (Simple)", simple)
    print_stats("Со сжатием (Compressed)", compressed)

    # Финальное сравнение судьёй
    print("\n===== JUDGE ANALYSIS (Simple vs Compressed) =====")
    judge_result = compare_sessions_with_judge(simple, compressed, simple_final, compressed_final)
    print(judge_result)


if __name__ == "__main__":
    main()
