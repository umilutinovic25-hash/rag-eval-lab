"""Local embeddings through Ollama, cached on disk so eval runs stay offline."""

import hashlib
import json
import math
import os
import tempfile
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


def load_cache(path: Path | None = None) -> dict:
    path = CACHE_PATH if path is None else path
    if not path.exists():
        return {}
    try:
        cache = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(cache, dict):
            raise ValueError("cache must be a JSON object")
        return cache
    except ValueError as error:
        raise EmbeddingError(f"Cache {path} is not a valid JSON object ({error}). Delete it to rebuild.") from error


def save_cache(cache: dict, path: Path | None = None) -> None:
    path = CACHE_PATH if path is None else path
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        tmp = Path(handle.name)
        try:
            handle.write(json.dumps(cache, sort_keys=True, allow_nan=False) + "\n")
        except Exception:
            tmp.unlink(missing_ok=True)
            raise
    try:
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def validate_vector(vector: list[float], dimension: int | None = None) -> int:
    if not isinstance(vector, list) or not vector:
        raise EmbeddingError("Embedding must be a nonempty list.")
    if dimension is not None and len(vector) != dimension:
        raise EmbeddingError("Embedding dimensions differ.")
    if any(type(value) not in (int, float) or not math.isfinite(value) for value in vector):
        raise EmbeddingError("Embedding values must be finite numbers.")
    return len(vector)


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
    dimension = None
    for vector in vectors:
        dimension = validate_vector(vector, dimension)
    return vectors


def embed(texts: list[str]) -> list[list[float]]:
    cache = load_cache()
    missing = [text for text in dict.fromkeys(texts) if cache_key(text) not in cache]
    if missing:
        for text, vector in zip(missing, request_embeddings(missing)):
            cache[cache_key(text)] = [round(value, 6) for value in vector]
        save_cache(cache)
    vectors = [cache[cache_key(text)] for text in texts]
    dimension = None
    for vector in vectors:
        dimension = validate_vector(vector, dimension)
    return vectors


def cosine(a: list[float], b: list[float]) -> float:
    dimension = validate_vector(a)
    validate_vector(b, dimension)
    # Scaling avoids overflow in squares, products and even the unscaled norm.
    scale_a, scale_b = max(abs(x) for x in a), max(abs(y) for y in b)
    if scale_a == 0 or scale_b == 0:
        return 0.0
    scaled_a = [x / scale_a for x in a]
    scaled_b = [y / scale_b for y in b]
    norm_a, norm_b = math.hypot(*scaled_a), math.hypot(*scaled_b)
    score = math.fsum((x / norm_a) * (y / norm_b) for x, y in zip(scaled_a, scaled_b))
    if not math.isfinite(score):
        raise EmbeddingError("Cosine result is not finite.")
    return max(-1.0, min(1.0, score))
