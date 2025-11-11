import os
import time
import json
import requests
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional
from urllib.parse import quote

from dotenv import load_dotenv
from transformers import AutoTokenizer

# ---------- .env ----------
load_dotenv()
HF_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN")
assert HF_TOKEN, "Add HUGGINGFACEHUB_API_TOKEN=hf_*** to your .env"

# ---------- Модели ----------
MODELS = [
    "google/gemma-2-2b-it",        # baseline (доступна у провайдеров Router’а)
    "Qwen/Qwen2.5-7B-Instruct",    # сильнее по качеству
]


# ---------- Промпт ----------
PROMPT = (
    "Отвечай строго на ру языке. "
    "Задача: объясни разницу между zero-shot, few-shot и fine-tuning. "
    "Когда что использовать и почему?"
)


# ---------- Параметры генерации ----------
GEN_PARAMS = {
    "max_new_tokens": 320,
    "temperature": 0.2,
    "top_p": 0.9,
    "repetition_penalty": 1.05,
}

# ---------- Стоимость (за 1k токенов, опционально) ----------
COSTS_PER_1K = {
    # "Qwen/Qwen2.5-7B-Instruct": {"input": 0.2, "output": 0.6},
    # "TinyLlama/TinyLlama-1.1B-Chat-v1.0": {"input": 0.05, "output": 0.15},
}

# ---------- HF Router endpoints ----------
ROUTER_MODEL_URL_TMPL = "https://router.huggingface.co/hf-inference/models/{model}"
ROUTER_CHAT_URL = "https://router.huggingface.co/v1/chat/completions"

HEADERS_JSON = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

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

# ---------- Token counting ----------
def num_tokens(model: str, text: str) -> int:
    """
    Пытаемся токенизировать выбранным токенайзером модели.
    Если нет доступа/ошибка — GPT-2.
    В крайнем случае — оценка по словам (чтобы не падать).
    """
    try:
        tok = AutoTokenizer.from_pretrained(model, use_fast=True, trust_remote_code=False)
        return len(tok.encode(text, add_special_tokens=False))
    except Exception:
        try:
            tok = AutoTokenizer.from_pretrained("gpt2", use_fast=True)
            return len(tok.encode(text, add_special_tokens=False))
        except Exception:
            return max(1, len(text.split()))

def estimate_cost_usd(model: str, input_toks: int, output_toks: int) -> float:
    pricing = COSTS_PER_1K.get(model) or {"input": 0.0, "output": 0.0}
    return (input_toks / 1000.0) * pricing["input"] + (output_toks / 1000.0) * pricing["output"]

# ---------- HTTP helpers ----------
def _safe_json(resp: requests.Response) -> Optional[Any]:
    """
    Пытаемся распарсить JSON; если не получилось (пусто/HTML) — вернём None.
    """
    try:
        return resp.json()
    except Exception:
        return None

def _router_model_inference(model: str, prompt: str) -> Dict[str, Any]:
    """
    Classic HF Router: POST /hf-inference/models/{model} c inputs.
    Возвращает dict с ключом 'ok' (bool) и 'data'/'error'/'status'/'raw'.
    """
    # В пути оставляем слэши, экранируем пробелы и т.п.
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
    # не-JSON/HTML/пусто
    if data is None:
        return {"ok": False, "error": f"Non-JSON response (classic). HTTP {resp.status_code}", "status": resp.status_code, "raw": resp.text[:400]}
    # JSON, но с ошибкой
    return {"ok": False, "error": f"HTTP {resp.status_code} (classic): {data}", "status": resp.status_code, "raw": data}

def _router_chat_completions(model: str, prompt: str) -> Dict[str, Any]:
    """
    Fallback: OpenAI-совместимый /v1/chat/completions.
    Возвращает dict с 'ok' и 'data'/'error'.
    """
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        # map базовых параметров
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
    Сначала пробуем classic Router → если не взлетает, пробуем chat-completions.
    С ретраями на оба режима.
    """
    last_err = None
    # 1) classic
    for attempt in range(1, retries + 1):
        r = _router_model_inference(model, prompt)
        if r.get("ok"):
            return {"mode": "classic", "data": r["data"]}
        last_err = r
        if attempt < retries:
            time.sleep(backoff * attempt)

    # 2) chat fallback
    for attempt in range(1, retries + 1):
        r = _router_chat_completions(model, prompt)
        if r.get("ok"):
            return {"mode": "chat", "data": r["data"]}
        last_err = r
        if attempt < retries:
            time.sleep(backoff * attempt)

    return {"mode": "none", "error": last_err.get("error", "Unknown error"), "raw": last_err.get("raw")}

# ---------- Ответ парсинг ----------
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
    # OpenAI-совместимый формат
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

# ---------- Основной прогон ----------
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

def run_once(model: str, prompt: str) -> RunResult:
    input_toks = num_tokens(model, prompt)

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

    output_toks = num_tokens(model, text)
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
          "   - См. точность, структуру, соответствие инструкции, примеры, отсутствие галлюцинаций.\n")

def main():
    results: List[RunResult] = []
    for m in MODELS:
        print(f"==> Running: {m}")
        res = run_once(m, PROMPT)
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
