#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import json
import requests
import tempfile
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional
from urllib.parse import quote
from pathlib import Path

from dotenv import load_dotenv
from transformers import AutoTokenizer, PreTrainedTokenizerFast
from huggingface_hub import hf_hub_download

# ========= ENV =========
load_dotenv()
from huggingface_hub import login, whoami
import os

HF_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN")
login(token=HF_TOKEN, add_to_git_credential=True)  # сохранит в git-credentials, удобно для git-lfs
print(whoami())  # быстрая проверка, что токен рабочий

assert HF_TOKEN, "Add HUGGINGFACEHUB_API_TOKEN=hf_*** to your .env"

# ========= MODELS =========
# По запросу: сравниваем именно эти две модели
MODELS = [
    "meta-llama/Llama-3.2-1B-Instruct",
    "Qwen/Qwen2.5-7B-Instruct",
]

# ========= PROMPT =========
PROMPT = (
    "Отвечай строго на русском языке. "
    "Задача: объясни разницу между zero-shot, few-shot и fine-tuning. "
    "Когда что использовать и почему? Коротко, но по делу."
)

# ========= GEN PARAMS =========
GEN_PARAMS = {
    "max_new_tokens": 320,
    "temperature": 0.2,
    "top_p": 0.9,
    "repetition_penalty": 1.05,
}

# ========= PRICING (optional) =========
# значения — $ за 1k токенов (пример; подставь реальные тарифы твоего провайдера)
COSTS_PER_1K = {
    # "meta-llama/Llama-3.2-1B-Instruct": {"input": 0.2, "output": 0.6},
    # "Qwen/Qwen2.5-7B-Instruct": {"input": 0.15, "output": 0.45},
}

# ========= HF Router endpoints =========
ROUTER_MODEL_URL_TMPL = "https://router.huggingface.co/hf-inference/models/{model}"
ROUTER_CHAT_URL = "https://router.huggingface.co/v1/chat/completions"

HEADERS_JSON = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

# ========= TOKENIZER FILE MAP (для ручной подгрузки) =========
# Qwen обычно доступен без проблем; для Llama — gated, поэтому пробуем скачать,
# иначе переключаемся на GPT-2 токенизатор.
TOKENIZER_FILES: Dict[str, List[str]] = {
    "meta-llama/Llama-3.2-1B-Instruct": [
        "tokenizer.json",
        "tokenizer_config.json",
        "special_tokens_map.json",
    ],
    "Qwen/Qwen2.5-7B-Instruct": [
        "tokenizer.json",
        "tokenizer_config.json",
        # у некоторых вариантов есть merges/vocab, но fast-версия из tokenizer.json покрывает кейс
    ],
}

# ========= DATA CLASSES =========
@dataclass
class RunResult:
    model: str
    latency_sec: float
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    text: str
    error: str = ""


# ========= TOKENIZER HELPERS =========
def try_download_tokenizer_dir(model: str) -> Optional[Path]:
    """
    Пытаемся скачать необходимые файлы токенайзера в локальную папку.
    Возвращает путь к папке или None, если не удалось (например, gated).
    """
    files = TOKENIZER_FILES.get(model)
    if not files:
        return None
    tmpdir = Path(tempfile.mkdtemp(prefix="tok_"))
    try:
        for fname in files:
            hf_hub_download(
                repo_id=model,
                filename=fname,
                local_dir=tmpdir,
                local_dir_use_symlinks=False,
                token=HF_TOKEN,
            )
        return tmpdir
    except Exception as e:
        print(f"⚠️ Не удалось скачать файлы токенайзера {model}: {e}")
        return None


def get_tokenizer(model: str) -> PreTrainedTokenizerFast:
    """
    Возвращает корректный токенайзер:
    1) Пытается авто-скачать из самого репо.
    2) Если не вышло (gated), пытается скачать нужные файлы вручную в temp.
    3) Если и это не удалось — падает на GPT-2 как на последний fallback (для подсчёта).
    """
    # Попытка обычной загрузки по имени модели
    try:
        tok = AutoTokenizer.from_pretrained(model, use_fast=True, trust_remote_code=False)
        _print_tok_info(model, tok, source="auto")
        return tok
    except Exception as auto_err:
        print(f"⚠️ Автозагрузка токенайзера для {model} не удалась: {auto_err}")

    # Попытка ручной загрузки файлов
    local_dir = try_download_tokenizer_dir(model)
    if local_dir:
        try:
            tok = AutoTokenizer.from_pretrained(str(local_dir), use_fast=True, trust_remote_code=False)
            _print_tok_info(model, tok, source=f"local:{local_dir}")
            return tok
        except Exception as local_err:
            print(f"⚠️ Локальная загрузка токенайзера для {model} не удалась: {local_err}")

    # Последний fallback — GPT-2 (подсчёт будет ≈, но лучше, чем ничего)
    tok = AutoTokenizer.from_pretrained("gpt2", use_fast=True)
    _print_tok_info(model, tok, source="fallback:gpt2")
    return tok


def _print_tok_info(model: str, tok: PreTrainedTokenizerFast, source: str):
    try:
        print(
            f"🔤 [{model}] tokenizer={tok.__class__.__name__} | "
            f"source={source} | vocab={getattr(tok, 'vocab_size', '?')} | "
            f"max_ctx={getattr(tok, 'model_max_length', '?')}"
        )
    except Exception:
        pass


def num_tokens(model: str, text: str, cache: Dict[str, PreTrainedTokenizerFast]) -> int:
    """
    Счёт токенов строго тем токенайзером, который мы решили использовать для этой модели.
    """
    if model not in cache:
        cache[model] = get_tokenizer(model)
    tok = cache[model]
    try:
        return len(tok.encode(text, add_special_tokens=False))
    except Exception:
        # если даже здесь что-то пойдёт не так — грубая оценка
        return max(1, len(text.split()))


def estimate_cost_usd(model: str, input_toks: int, output_toks: int) -> float:
    pricing = COSTS_PER_1K.get(model) or {"input": 0.0, "output": 0.0}
    return (input_toks / 1000.0) * pricing["input"] + (output_toks / 1000.0) * pricing["output"]


# ========= HTTP HELPERS =========
def _safe_json(resp: requests.Response) -> Optional[Any]:
    try:
        return resp.json()
    except Exception:
        return None


def _router_model_inference(model: str, prompt: str) -> Dict[str, Any]:
    """
    Classic HF Router: POST /hf-inference/models/{model} c inputs.
    """
    model_path = quote(model, safe="/")
    url = ROUTER_MODEL_URL_TMPL.format(model=model_path)
    payload = {
        "inputs": prompt,
        "parameters": GEN_PARAMS,
        "options": {"use_cache": True, "wait_for_model": True},
    }
    try:
        resp = requests.post(url, headers=HEADERS_JSON, data=json.dumps(payload), timeout=180)
    except Exception as e:
        return {"ok": False, "error": f"Request error (classic): {e}"}

    data = _safe_json(resp)
    if resp.status_code == 200 and data is not None:
        return {"ok": True, "data": data}
    if data is None:
        return {"ok": False, "error": f"Non-JSON response (classic). HTTP {resp.status_code}", "status": resp.status_code, "raw": resp.text[:400]}
    return {"ok": False, "error": f"HTTP {resp.status_code} (classic): {data}", "status": resp.status_code, "raw": data}


def _router_chat_completions(model: str, prompt: str) -> Dict[str, Any]:
    """
    Fallback: OpenAI-совместимый /v1/chat/completions.
    """
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        "temperature": GEN_PARAMS.get("temperature", 0.7),
        "top_p": GEN_PARAMS.get("top_p", 1.0),
        "max_tokens": GEN_PARAMS.get("max_new_tokens", 256),
    }
    try:
        resp = requests.post(ROUTER_CHAT_URL, headers=HEADERS_JSON, data=json.dumps(payload), timeout=180)
    except Exception as e:
        return {"ok": False, "error": f"Request error (chat): {e}"}

    data = _safe_json(resp)
    if resp.status_code == 200 and data is not None:
        return {"ok": True, "data": data}
    if data is None:
        return {"ok": False, "error": f"Non-JSON response (chat). HTTP {resp.status_code}", "status": resp.status_code, "raw": resp.text[:400]}
    return {"ok": False, "error": f"HTTP {resp.status_code} (chat): {data}", "status": resp.status_code, "raw": data}


def call_hf(model: str, prompt: str, retries: int = 3, backoff: float = 5.0) -> Dict[str, Any]:
    """
    Сначала пробуем classic Router → если не взлетает, пробуем chat-completions (оба с ретраями).
    """
    last_err = None
    # classic
    for attempt in range(1, retries + 1):
        r = _router_model_inference(model, prompt)
        if r.get("ok"):
            return {"mode": "classic", "data": r["data"]}
        last_err = r
        if attempt < retries:
            time.sleep(backoff * attempt)

    # chat fallback
    for attempt in range(1, retries + 1):
        r = _router_chat_completions(model, prompt)
        if r.get("ok"):
            return {"mode": "chat", "data": r["data"]}
        last_err = r
        if attempt < retries:
            time.sleep(backoff * attempt)

    return {"mode": "none", "error": last_err.get("error", "Unknown error"), "raw": last_err.get("raw")}


# ========= PARSERS =========
def extract_text_from_classic(data: Any) -> str:
    if isinstance(data, list) and data:
        item = data[0]
        if isinstance(item, dict):
            if "generated_text" in item and isinstance(item["generated_text"], str):
                return item["generated_text"]
            for k in ["output_text", "text", "content"]:
                if k in item and isinstance(item[k], str):
                    return item[k]
    if isinstance(data, dict):
        for k in ["generated_text", "text", "output_text", "content"]:
            if k in data and isinstance(data[k], str):
                return data[k]
    return ""


def extract_text_from_chat(data: Dict[str, Any]) -> str:
    try:
        choices = data.get("choices") or []
        if choices and "message" in choices[0]:
            return choices[0]["message"].get("content", "") or ""
    except Exception:
        pass
    return ""


def extract_text(mode: str, data: Any) -> str:
    if mode == "classic":
        return extract_text_from_classic(data)
    if mode == "chat":
        return extract_text_from_chat(data)
    return ""


# ========= MAIN RUN =========
def run_once(model: str, prompt: str, tcache: Dict[str, PreTrainedTokenizerFast]) -> RunResult:
    input_toks = num_tokens(model, prompt, tcache)

    t0 = time.perf_counter()
    resp = call_hf(model, prompt)
    dt = round(time.perf_counter() - t0, 3)

    if "error" in resp and resp.get("mode") == "none":
        return RunResult(
            model=model,
            latency_sec=dt,
            input_tokens=input_toks,
            output_tokens=0,
            total_tokens=input_toks,
            cost_usd=estimate_cost_usd(model, input_toks, 0),
            text="",
            error=f"{resp.get('error')} | raw: {str(resp.get('raw'))[:180]}",
        )

    mode = resp.get("mode", "classic")
    data = resp.get("data")
    text = extract_text(mode, data)
    if not text:
        return RunResult(
            model=model,
            latency_sec=dt,
            input_tokens=input_toks,
            output_tokens=0,
            total_tokens=input_toks,
            cost_usd=estimate_cost_usd(model, input_toks, 0),
            text="",
            error=f"Cannot parse response ({mode}). Snippet: {str(data)[:180]}",
        )

    output_toks = num_tokens(model, text, tcache)
    total = input_toks + output_toks
    cost = estimate_cost_usd(model, input_toks, output_toks)

    return RunResult(
        model=model,
        latency_sec=dt,
        input_tokens=input_toks,
        output_tokens=output_toks,
        total_tokens=total,
        cost_usd=round(cost, 6),
        text=text.strip(),
        error=""
    )


def pretty_print(results: List[RunResult]):
    header = f"{'Model':40s} {'Latency(s)':>10s} {'In':>6s} {'Out':>6s} {'Total':>7s} {'Cost($)':>8s}"
    print(header)
    print("-" * len(header))
    for r in results:
        print(f"{r.model[:40]:40s} {r.latency_sec:10.3f} {r.input_tokens:6d} {r.output_tokens:6d} {r.total_tokens:7d} {r.cost_usd:8.4f}")
        if r.error:
            print(f"   ERROR: {r.error}")
    print("\n▼ Краткий вывод по качеству (оценка вручную):\n"
          "   - Смотри точность, структуру, соответствие инструкции, примеры, отсутствие галлюцинаций.\n")


def main():
    tcache: Dict[str, PreTrainedTokenizerFast] = {}
    results: List[RunResult] = []

    for m in MODELS:
        print(f"==> Running: {m}")
        res = run_once(m, PROMPT, tcache)
        results.append(res)

    pretty_print(results)

    out = [asdict(r) for r in results]
    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print("\n=== Ответы моделей ===\n")
    for r in results:
        print(f"[{r.model}]")
        if r.error:
            print(f"ERROR: {r.error}\n")
        else:
            print(r.text + "\n")


if __name__ == "__main__":
    main()
