"""Local LLM calls through Ollama, cached on disk so eval runs stay offline and deterministic."""

import hashlib
import json
import urllib.request

from . import config
from .embeddings import CACHE_PATH as EMBEDDING_CACHE_PATH, load_cache, save_cache


CACHE_PATH = EMBEDDING_CACHE_PATH.with_name("llm_cache.json")
OLLAMA_URL = "http://localhost:11434/api/generate"
ACCEPT_WORDS = {"yes", "relevant"}


class LLMError(RuntimeError):
    """Raised when a prompt is not cached and Ollama cannot answer it."""


def cache_key(model: str, prompt: str, max_tokens: int) -> str:
    return hashlib.sha256(f"{model}\n{max_tokens}\n{prompt}".encode("utf-8")).hexdigest()


def request_generation(model: str, prompt: str, max_tokens: int) -> str:
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0, "seed": 7, "num_predict": max_tokens},
        }
    ).encode("utf-8")
    request = urllib.request.Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            text = json.load(response)["response"]
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise LLMError(f"Uncached prompt needs Ollama with model {model!r} at {OLLAMA_URL} ({error}).") from error
    if not isinstance(text, str):
        raise LLMError(f"Ollama returned no text for model {model!r}.")
    return text


def generate(model: str, prompt: str, max_tokens: int) -> str:
    cache = load_cache(CACHE_PATH)
    key = cache_key(model, prompt, max_tokens)
    if key not in cache:
        cache[key] = request_generation(model, prompt, max_tokens).strip()
        save_cache(cache, CACHE_PATH)
    return cache[key]


def passage_answers(question: str, passage: str) -> bool:
    reply = generate(config.RERANK_MODEL, config.RERANK_PROMPT.format(question=question, passage=passage), 3)
    words = reply.lower().split()
    return bool(words) and words[0].strip(".,!:") in ACCEPT_WORDS


def write_answer(question: str, passages: list[tuple[str, str]]) -> str:
    listed = "\n".join(f"[{chunk_id}] {text}" for chunk_id, text in passages)
    prompt = config.GENERATION_PROMPT.format(passages=listed, question=question)
    return generate(config.GENERATION_MODEL, prompt, 80)
