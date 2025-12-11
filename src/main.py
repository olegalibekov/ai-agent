#!/usr/bin/env python3
import sys
import time
import textwrap
from typing import Dict, Any

import requests

# =============================================================================
# БАЗОВЫЕ НАСТРОЙКИ
# =============================================================================

OLLAMA_URL = "http://localhost:11434/api/chat"

# =============================================================================
# ДЛИННЫЙ ТЕКСТ ДЛЯ СУММАРИЗАЦИИ
# =============================================================================

TEXT_TO_SUMMARIZE = (
    "Машинного обучение стремительно развивается, и современные нейронные сети "
    "становятся требовательнее к вычислительным ресурсам. "
    "В результате растёт время обучения моделей, увеличиваются затраты на энергию и "
    "происходит усложнение инфраструктуры, необходимой для их развертывания. "
    "Компании и исследователи сталкиваются с задачей оптимизации больших моделей без "
    "существенной потери качества. Среди наиболее эффективных техник выделяются "
    "квантование, pruning и дистилляция. Квантование уменьшает разрядность чисел, "
    "которые используются для хранения весов модели, что позволяет значительно "
    "уменьшить размер модели и ускорить вычисления. Pruning удаляет "
    "малоинформативные связи и нейроны, уменьшая сложность сети. "
    "Дистилляция передает знания от большой модели маленькой, "
    "что позволяет получить компактную модель, сохраняющую высокую точность. "
    "Эти методы особенно полезны для развёртывания моделей на мобильных устройствах "
    "и в IoT-среде, где ресурсы ограничены. Техники оптимизации позволяют "
    "существенно снизить стоимость инфраструктуры и повысить доступность технологий."
)

# =============================================================================
# МОДЕЛИ + ПАРАМЕТРЫ
# =============================================================================

MODEL_CONFIGS = {
    "q4_small_ctx_hot": {
        "model": "qwen2.5:3b-instruct-q4_0",
        "num_ctx": 2048,
        "temperature": 0.7,
        "max_tokens": 128,
        "description": "Q4: малое окно, высокая температура, короткий ответ",
    },
    "q4_medium_ctx": {
        "model": "qwen2.5:3b-instruct-q4_0",
        "num_ctx": 4096,
        "temperature": 0.3,
        "max_tokens": 256,
        "description": "Q4: среднее окно, умеренная температура",
    },
    "q4_large_ctx_cold": {
        "model": "qwen2.5:3b-instruct-q4_0",
        "num_ctx": 8192,
        "temperature": 0.1,
        "max_tokens": 384,
        "description": "Q4: большое окно, низкая температура",
    },

    "q8_medium_ctx": {
        "model": "qwen2.5:3b-instruct-q8_0",
        "num_ctx": 4096,
        "temperature": 0.3,
        "max_tokens": 256,
        "description": "Q8: среднее окно, лучшее качество",
    },
    "q8_large_ctx_cold": {
        "model": "qwen2.5:3b-instruct-q8_0",
        "num_ctx": 8192,
        "temperature": 0.1,
        "max_tokens": 384,
        "description": "Q8: большое окно, почти full precision",
    },

    "full_large_ctx_cold": {
        "model": "qwen2.5:3b-instruct",
        "num_ctx": 8192,
        "temperature": 0.1,
        "max_tokens": 384,
        "description": "FULL: максимальное качество",
    },
}

# =============================================================================
# PROMPT
# =============================================================================

SYSTEM_PROMPT = (
    "Ты — ассистент, специализирующийся на суммаризации. "
    "Сделай краткое и точное резюме текста в 2–3 предложениях. "
    "Не добавляй новых фактов."
)

PROMPT_TEMPLATE = """
Текст:
{TEXT}

Инструкция:
Сделай краткое резюме текста (2–3 предложения).
""".strip()


# =============================================================================
# ФУНКЦИИ ЗАПРОСОВ
# =============================================================================

def build_payload(config: Dict[str, Any], text: str) -> Dict[str, Any]:
    return {
        "model": config["model"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": PROMPT_TEMPLATE.format(TEXT=text)},
        ],
        "stream": False,
        "options": {
            "num_ctx": config["num_ctx"],
            "temperature": config["temperature"],
            "num_predict": config["max_tokens"],
        },
    }


def ask_ollama(config_name: str, text: str) -> Dict[str, Any]:
    config = MODEL_CONFIGS[config_name]
    payload = build_payload(config, text)

    start = time.time()
    response = requests.post(OLLAMA_URL, json=payload)
    elapsed = time.time() - start

    response.raise_for_status()
    data = response.json()

    content = data["message"]["content"]

    return {
        "config": config_name,
        "answer": content,
        "elapsed": elapsed,
        "len_chars": len(content),
    }


# =============================================================================
# БЕНЧМАРК
# =============================================================================

def run_benchmark(text: str):
    print("=" * 80)
    print("БЕНЧМАРК СУММАРИЗАЦИИ — разные q4/q8/full + разные параметры")
    print("=" * 80)
    print("\nТЕКСТ ДЛЯ СУММАРИЗАЦИИ:")
    print(textwrap.indent(text, "    "))
    print("=" * 80)

    for name, cfg in MODEL_CONFIGS.items():
        print("\n" + "-" * 80)
        print(f"Конфиг: {name}")
        print(f"Описание: {cfg['description']}")
        print(f"Модель: {cfg['model']}")
        print(f"num_ctx={cfg['num_ctx']}, temperature={cfg['temperature']}, max_tokens={cfg['max_tokens']}")
        print("-" * 80)

        try:
            result = ask_ollama(name, text)
        except Exception as e:
            print(f"Ошибка запроса: {e}")
            continue

        print(f"\nВремя ответа: {result['elapsed']:.2f} сек")
        print(f"Длина ответа: {result['len_chars']} символов")
        print("Ответ:")
        print(textwrap.indent(result["answer"].strip(), "    "))


# =============================================================================
# CLI
# =============================================================================

def print_help():
    print("Использование:")
    print("  benchmark — сравнить все конфиги")
    print('  "текст"   — суммаризировать один текст (конфиг: q8_large_ctx_cold)')


def main():
    if len(sys.argv) == 1:
        print_help()
        return

    if sys.argv[1] == "benchmark":
        run_benchmark(TEXT_TO_SUMMARIZE)
        return

    # одиночное суммари
    text = " ".join(sys.argv[1:])
    result = ask_ollama("q8_large_ctx_cold", text)

    print("\nТЕКСТ ДЛЯ СУММАРИЗАЦИИ:")
    print(textwrap.indent(text, "    "))
    print("\nОТВЕТ:")
    print(result["answer"])


if __name__ == "__main__":
    main()
