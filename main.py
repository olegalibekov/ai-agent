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
from huggingface_hub import hf_hub_download, login, whoami

# ========= ENV =========
load_dotenv()

HF_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN")
assert HF_TOKEN, "Add HUGGINGFACEHUB_API_TOKEN=hf_*** to your .env"

# логин в HF (сохранит токен в git-credentials, удобно для lfs)
login(token=HF_TOKEN, add_to_git_credential=True)
print("HF whoami:", whoami())

# ========= MODEL =========
MODEL = "Qwen/Qwen2.5-7B-Instruct"
MODELS = [MODEL]

# ========= PROMPTS (3 кейса) =========
PROMPTS: Dict[str, str] = {
    "short": (
        "Отвечай строго на русском языке. "
        "Коротко объясни разницу между zero-shot, few-shot и fine-tuning (2–3 предложения)."
    ),
    "long": (
        "Отвечай строго на русском языке. "
        "Подробно и по шагам объясни разницу между zero-shot, few-shot и fine-tuning, "
        "приведи несколько практических примеров из индустрии, опиши плюсы и минусы каждого подхода, "
        "сравни их по стоимости, качеству и сложности внедрения, а также дай рекомендации, "
        "какой подход выбирать для прототипа, для production-системы и для узкоспециализированных задач. "
        "Разверни ответ, сделай структурированным и хорошо аргументированным."
    ),
    "too_long": (
        "Отвечай строго на русском языке. Перед тем как дать объяснение, сначала многократно повтори следующий текст, "
        "а затем в конце всё равно кратко объясни разницу между zero-shot, few-shot и fine-tuning:\n\n"
        + ("ZERO-SHOT FEW-SHOT FINE-TUNING — повторяй эту фразу. " * 4000)
    ),
}

# ========= GEN PARAMS =========
GEN_PARAMS = {
    "temperature": 0.3,
    "repetition_penalty": 1.0,
    # "max_new_tokens": 256,
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
TOKENIZER_FILES: Dict[str, List[str]] = {
    "Qwen/Qwen2.5-7B-Instruct": [
        "tokenizer.json",
        "tokenizer_config.json",
    ],
}


# ========= DATA CLASSES =========
@dataclass
class RunResult:
    model: str
    prompt_name: str          # short / long / too_long
    latency_sec: float
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    text: str
    error: str = ""
    model_max_length: Optional[int] = None
    over_limit_estimate: bool = False  # total_tokens > model_max_length ?


# ========= TOKENIZER HELPERS =========
def try_download_tokenizer_dir(model: str) -> Optional[Path]:
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


def _print_tok_info(model: str, tok: PreTrainedTokenizerFast, source: str):
    try:
        print(
            f"🔤 [{model}] tokenizer={tok.__class__.__name__} | "
            f"source={source} | vocab={getattr(tok, 'vocab_size', 'n/a')} | "
            f"max_ctx={getattr(tok, 'model_max_length', 'n/a')}"
        )
    except Exception:
        pass


def debug_tokenizer_sample(model: str, tok: PreTrainedTokenizerFast, sample: str = "Привет, мир!"):
    try:
        ids = tok.encode(sample, add_special_tokens=False)
    except Exception:
        ids = []
    try:
        print(ids)
        print("🔤 Класс токенайзера:", tok.__class__.__name__)
        print("🔢 Размер словаря:", getattr(tok, "vocab_size", "n/a"))
    except Exception:
        pass


# ========= PRICING (optional) =========
COSTS_PER_1K = {
    # "Qwen/Qwen2.5-7B-Instruct": {"input": 0.15, "output": 0.45},
}

def get_tokenizer(model: str) -> PreTrainedTokenizerFast:
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

    # Последний fallback — GPT-2 (подсчёт будет ≈)
    tok = AutoTokenizer.from_pretrained("gpt2", use_fast=True)
    _print_tok_info(model, tok, source="fallback:gpt2")
    return tok


def num_tokens(model: str, text: str, cache: Dict[str, PreTrainedTokenizerFast]) -> int:
    if model not in cache:
        cache[model] = get_tokenizer(model)
    tok = cache[model]
    try:
        return len(tok.encode(text, add_special_tokens=False))
    except Exception:
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
        return {
            "ok": False,
            "error": f"Non-JSON response (classic). HTTP {resp.status_code}",
            "status": resp.status_code,
            "raw": resp.text[:400],
        }
    return {
        "ok": False,
        "error": f"HTTP {resp.status_code} (classic): {data}",
        "status": resp.status_code,
        "raw": data,
    }


def _router_chat_completions(model: str, prompt: str) -> Dict[str, Any]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        "temperature": GEN_PARAMS.get("temperature", 0.7),
        "top_p": GEN_PARAMS.get("top_p", 1.0),
        # "max_tokens": GEN_PARAMS.get("max_new_tokens", 256),
    }
    try:
        resp = requests.post(ROUTER_CHAT_URL, headers=HEADERS_JSON, data=json.dumps(payload), timeout=180)
    except Exception as e:
        return {"ok": False, "error": f"Request error (chat): {e}"}

    data = _safe_json(resp)
    if resp.status_code == 200 and data is not None:
        return {"ok": True, "data": data}
    if data is None:
        return {
            "ok": False,
            "error": f"Non-JSON response (chat). HTTP {resp.status_code}",
            "status": resp.status_code,
            "raw": resp.text[:400],
        }
    return {
        "ok": False,
        "error": f"HTTP {resp.status_code} (chat): {data}",
        "status": resp.status_code,
        "raw": data,
    }


def call_hf(model: str, prompt: str, retries: int = 3, backoff: float = 5.0) -> Dict[str, Any]:
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

    return {
        "mode": "none",
        "error": last_err.get("error", "Unknown error"),
        "raw": last_err.get("raw"),
    }


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
def run_once(model: str, prompt_name: str, prompt: str, tcache: Dict[str, PreTrainedTokenizerFast]) -> RunResult:
    if model not in tcache:
        tcache[model] = get_tokenizer(model)
    tok = tcache[model]

    input_toks = num_tokens(model, prompt, tcache)
    model_max_length = getattr(tok, "model_max_length", None)

    t0 = time.perf_counter()
    resp = call_hf(model, prompt)
    dt = round(time.perf_counter() - t0, 3)

    over_limit_estimate = bool(
        model_max_length is not None and input_toks > model_max_length
    )

    if "error" in resp and resp.get("mode") == "none":
        return RunResult(
            model=model,
            prompt_name=prompt_name,
            latency_sec=dt,
            input_tokens=input_toks,
            output_tokens=0,
            total_tokens=input_toks,
            cost_usd=estimate_cost_usd(model, input_toks, 0),
            text="",
            error=f"{resp.get('error')} | raw: {str(resp.get('raw'))[:180]}",
            model_max_length=model_max_length,
            over_limit_estimate=over_limit_estimate,
        )

    mode = resp.get("mode", "classic")
    data = resp.get("data")
    text = extract_text(mode, data)
    if not text:
        return RunResult(
            model=model,
            prompt_name=prompt_name,
            latency_sec=dt,
            input_tokens=input_toks,
            output_tokens=0,
            total_tokens=input_toks,
            cost_usd=estimate_cost_usd(model, input_toks, 0),
            text="",
            error=f"Cannot parse response ({mode}). Snippet: {str(data)[:180]}",
            model_max_length=model_max_length,
            over_limit_estimate=over_limit_estimate,
        )

    output_toks = num_tokens(model, text, tcache)
    total = input_toks + output_toks
    cost = estimate_cost_usd(model, input_toks, output_toks)

    over_limit_estimate = bool(
        model_max_length is not None and total > model_max_length
    )

    return RunResult(
        model=model,
        prompt_name=prompt_name,
        latency_sec=dt,
        input_tokens=input_toks,
        output_tokens=output_toks,
        total_tokens=total,
        cost_usd=round(cost, 6),
        text=text.strip(),
        error="",
        model_max_length=model_max_length,
        over_limit_estimate=over_limit_estimate,
    )


def pretty_print(results: List[RunResult]):
    header = (
        f"{'Model':28s} {'Prompt':10s} {'Latency(s)':>10s} "
        f"{'In':>6s} {'Out':>6s} {'Total':>7s} {'Ctx':>7s} {'>Ctx?':>6s}"
    )
    print(header)
    print("-" * len(header))
    for r in results:
        ctx_str = str(r.model_max_length) if r.model_max_length is not None else "-"
        over_str = "Y" if r.over_limit_estimate else "N"
        print(
            f"{r.model[:28]:28s} {r.prompt_name[:10]:10s} "
            f"{r.latency_sec:10.3f} {r.input_tokens:6d} {r.output_tokens:6d} "
            f"{r.total_tokens:7d} {ctx_str:>7s} {over_str:>6s}"
        )
        if r.error:
            print(f"   ERROR: {r.error}")


def compare_tokenizers(models: List[str], tcache: Dict[str, PreTrainedTokenizerFast], sample: str = "Привет, мир!"):
    print("\n=== Tokenizer check on sample:", repr(sample), "===\n")
    for m in models:
        if m not in tcache:
            tcache[m] = get_tokenizer(m)
        tok = tcache[m]
        _print_tok_info(m, tok, source=getattr(tok, "name_or_path", "auto"))
        debug_tokenizer_sample(m, tok, sample)
        print("-" * 60)


def main():
    tcache: Dict[str, PreTrainedTokenizerFast] = {}

    # 1) Сравнение токенайзера на "Привет, мир!"
    compare_tokenizers(MODELS, tcache, sample="Привет, мир!")

    # 2) Прогон инференса и метрик для трёх типов промптов
    results: List[RunResult] = []

    for pname, prompt in PROMPTS.items():
        print(f"\n=== Prompt: {pname} (chars={len(prompt)}) ===\n")
        print(f"==> Running: {MODEL}")
        res = run_once(MODEL, pname, prompt, tcache)
        results.append(res)

    print("\n=== Summary table ===\n")
    pretty_print(results)

    out = [asdict(r) for r in results]
    with open("results_qwen.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print("\n=== Ответы модели по промптам ===\n")
    for pname in PROMPTS.keys():
        print(f"\n##### Prompt: {pname} #####\n")
        for r in results:
            if r.prompt_name != pname:
                continue
            print(f"[{r.model}]")
            if r.error:
                print(f"ERROR: {r.error}\n")
            else:
                print(r.text + "\n")


if __name__ == "__main__":
    main()
