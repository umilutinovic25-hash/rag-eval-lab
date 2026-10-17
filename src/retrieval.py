from dataclasses import dataclass
import re

from . import config
from .chunking import Chunk
from .embeddings import cosine, embed


TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")


def tokenize(text: str) -> list[str]:
    tokens = [token.lower() for token in TOKEN_RE.findall(text)]
    if config.STOPWORDS_ENABLED:
        raise NotImplementedError("STOPWORDS_ENABLED = True is not implemented yet.")
    return tokens


@dataclass(frozen=True)
class RetrievalResult:
    chunk: Chunk
    score: float


def lexical_score(query: str, chunk_text: str) -> float:
    q_tokens = tokenize(query)
    c_tokens = tokenize(chunk_text)
    if not q_tokens or not c_tokens:
        return 0.0

    q_set = set(q_tokens)
    overlap = sum(1 for token in c_tokens if token in q_set)
    return overlap / len(c_tokens)


RRF_K = 60


def semantic_scores(query: str, chunks: list[Chunk]) -> list[float]:
    if not chunks:
        return []
    query_vector, *chunk_vectors = embed([query] + [chunk.text for chunk in chunks])
    return [cosine(query_vector, vector) for vector in chunk_vectors]


def ranks(scores: list[float]) -> list[int]:
    order = sorted(range(len(scores)), key=lambda i: -scores[i])
    rank = [0] * len(scores)
    for position, index in enumerate(order, start=1):
        rank[index] = position
    return rank


def score_chunks(query: str, chunks: list[Chunk]) -> list[float]:
    if config.RETRIEVAL_MODE == "lexical":
        return [lexical_score(query, chunk.text) for chunk in chunks]
    if config.RETRIEVAL_MODE in ("semantic", "hybrid"):
        return semantic_scores(query, chunks)
    raise ValueError(f"Unknown RETRIEVAL_MODE: {config.RETRIEVAL_MODE}")


def sort_keys(query: str, chunks: list[Chunk], scores: list[float]) -> list[float]:
    """Higher is better. Hybrid orders by Reciprocal Rank Fusion; the reported score stays cosine."""
    if config.RETRIEVAL_MODE != "hybrid":
        return scores
    lexical_rank = ranks([lexical_score(query, chunk.text) for chunk in chunks])
    semantic_rank = ranks(scores)
    return [1 / (RRF_K + a) + 1 / (RRF_K + b) for a, b in zip(lexical_rank, semantic_rank)]


def searchable_chunks(chunks: list[Chunk]) -> list[Chunk]:
    if config.CURRENT_ONLY:
        return [chunk for chunk in chunks if chunk.status != "superseded"]
    return chunks


def retrieve_top_k(query: str, chunks: list[Chunk], k: int | None = None) -> list[RetrievalResult]:
    k = config.TOP_K if k is None else k
    if k <= 0:
        raise ValueError("k must be > 0")

    candidates = searchable_chunks(chunks)
    scores = score_chunks(query, candidates)
    keys = sort_keys(query, candidates, scores)
    scored = [
        (key, RetrievalResult(chunk=chunk, score=score))
        for chunk, score, key in zip(candidates, scores, keys)
    ]
    filtered = [(key, item) for key, item in scored if item.score >= config.RETRIEVAL_MIN_SCORE]
    filtered.sort(key=lambda pair: (-pair[0], pair[1].chunk.chunk_id))
    return [item for _, item in filtered[:k]]
