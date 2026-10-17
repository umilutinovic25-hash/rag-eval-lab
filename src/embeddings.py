"""Local embeddings through Ollama, cached on disk so eval runs stay offline."""

import hashlib
import json
import math
import os
import urllib.error
import urllib.request
from pathlib import Path

from . import config


CACHE_PATH = Path(__file__).resolve().parents[1] / "data" / "embedding_cache.json"
OLLAMA_URL = "http://localhost:11434/api/embed"


class EmbeddingError(RuntimeError):
    pass


def cache_key(text: str, model: str | None = None) -> str:
    model = config.EMBEDDING_MODEL if model is None else model
    return hashlib.sha256(f"{model}\n{text}".encode("utf-8")).hexdigest()


def load_cache(path: Path | None = None) -> dict[str, list[float]]:
    path = CACHE_PATH if path is None else path
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except ValueError as error:
        raise EmbeddingError(f"Embedding cache {path} is not valid JSON ({error}). Delete it to rebuild.") from error


def save_cache(cache: dict[str, list[float]], path: Path | None = None) -> None:
    path = CACHE_PATH if path is None else path
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(cache, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def request_embeddings(texts: list[str]) -> list[list[float]]:
    payload = json.dumps({"model": config.EMBEDDING_MODEL, "input": texts}).encode("utf-8")
    request = urllib.request.Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            vectors = json.load(response)["embeddings"]
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise EmbeddingError(
            f"Embedding {len(texts)} uncached text(s) needs Ollama with model "
            f"{config.EMBEDDING_MODEL!r} at {OLLAMA_URL} ({error})."
        ) from error
    if not isinstance(vectors, list) or len(vectors) != len(texts):
        raise EmbeddingError(f"Ollama returned {len(vectors) if isinstance(vectors, list) else 'no'} vectors for {len(texts)} text(s).")
    return vectors


def embed(texts: list[str]) -> list[list[float]]:
    cache = load_cache()
    missing = [text for text in dict.fromkeys(texts) if cache_key(text) not in cache]
    if missing:
        for text, vector in zip(missing, request_embeddings(missing)):
            cache[cache_key(text)] = [round(value, 6) for value in vector]
        save_cache(cache)
    return [cache[cache_key(text)] for text in texts]


def cosine(a: list[float], b: list[float]) -> float:
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    if norm == 0:
        return 0.0
    return sum(x * y for x, y in zip(a, b)) / norm
