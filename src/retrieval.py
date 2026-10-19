from dataclasses import dataclass
import math
import re

from . import config
from .chunking import Chunk
from .embeddings import cosine, embed
from .language_tools import fold


TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")


def tokenize(text: str) -> list[str]:
    tokens = TOKEN_RE.findall(fold(text))
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


def chunk_embedding_text(chunk: Chunk) -> str:
    return f"{chunk.title}: {chunk.text}" if config.CHUNK_HEADERS else chunk.text


def bm25_scores(query: str, chunks: list[Chunk]) -> list[float]:
    """Okapi BM25 with IDF over the searched chunks (the corpus statistics are those of the candidates)."""
    documents = [tokenize(chunk.text) for chunk in chunks]
    if not documents:
        return []
    average = sum(len(tokens) for tokens in documents) / len(documents) or 1.0
    terms = set(tokenize(query))
    frequency = {term: sum(1 for tokens in documents if term in tokens) for term in terms}
    scores = []
    for tokens in documents:
        score = 0.0
        for term in terms:
            count = tokens.count(term)
            if not count:
                continue
            idf = math.log(1 + (len(documents) - frequency[term] + 0.5) / (frequency[term] + 0.5))
            norm = count + config.BM25_K1 * (1 - config.BM25_B + config.BM25_B * len(tokens) / average)
            score += idf * count * (config.BM25_K1 + 1) / norm
        scores.append(score)
    return scores


def min_max(values: list[float]) -> list[float]:
    low, high = min(values), max(values)
    return [0.0 if high == low else (value - low) / (high - low) for value in values]


def semantic_scores(query: str, chunks: list[Chunk]) -> list[float]:
    if not chunks:
        return []
    query_vector, *chunk_vectors = embed([query] + [chunk_embedding_text(chunk) for chunk in chunks])
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
    if config.RETRIEVAL_MODE == "bm25":
        return bm25_scores(query, chunks)
    if config.RETRIEVAL_MODE in config.COSINE_MODES:
        return semantic_scores(query, chunks)
    raise ValueError(f"Unknown RETRIEVAL_MODE: {config.RETRIEVAL_MODE}")


def sort_keys(query: str, chunks: list[Chunk], scores: list[float]) -> list[float]:
    """Higher is better. Hybrid orders by Reciprocal Rank Fusion; the reported score stays cosine."""
    if config.RETRIEVAL_MODE == "hybrid-bm25":
        if not chunks:
            return []
        semantic, keyword = min_max(scores), min_max(bm25_scores(query, chunks))
        weight = config.HYBRID_WEIGHT
        return [weight * a + (1 - weight) * b for a, b in zip(semantic, keyword)]
    if config.RETRIEVAL_MODE != "hybrid":
        return scores
    lexical_rank = ranks([lexical_score(query, chunk.text) for chunk in chunks])
    semantic_rank = ranks(scores)
    return [1 / (RRF_K + a) + 1 / (RRF_K + b) for a, b in zip(lexical_rank, semantic_rank)]


YEAR_RE = re.compile(r"\b(20\d{2})\b")
# A past word counts only next to a policy noun, so "previous instructions" or "is used to reserve" do not trigger it.
PAST_RE = re.compile(
    r"\b(?:previous|previously|old|older|former|formerly|earlier|prior)\b(?:\W+\w+){0,3}?\W+"
    r"(?:policy|policies|rules?|version|limit|window|terms|allowance|price)\b"
    r"|\bbefore (?:it|that|this|the (?:rule|policy|limit)) changed\b"
    r"|\bused to (?:be|allow|have|get|give|take|pay)\b",
    re.I,
)
BEFORE_PRESENT_RE = re.compile(r"\b(?:before|prior to) (?:the )?(?:current|new|latest)\b", re.I)
BEFORE_YEAR_RE = re.compile(r"\b(?:before|prior to)\b[^.?]*?\b(20\d{2})\b", re.I)
PRESENT_RE = re.compile(r"\b(now|currently|current|today|still|anymore|any more|latest)\b", re.I)


def requested_versions(query: str | None, versions: set[str]) -> set[str] | None:
    """Versions the question asks for, or None for the default (current only)."""
    if not query or not config.HISTORICAL_VERSIONS:
        return None
    before = BEFORE_YEAR_RE.search(query)
    if before:
        return {v for v in versions if v < before.group(1)}
    years = set(YEAR_RE.findall(query))
    if years:
        return years
    if BEFORE_PRESENT_RE.search(query) or (PAST_RE.search(query) and not PRESENT_RE.search(query)):
        return {"superseded"}
    return None


def historical_mode(query: str | None, chunks: list[Chunk]) -> bool:
    versioned = {chunk.title for chunk in chunks if chunk.status == "superseded"}
    return config.CURRENT_ONLY and requested_versions(query, {c.version for c in chunks if c.title in versioned}) is not None


def searchable_chunks(chunks: list[Chunk], query: str | None = None) -> list[Chunk]:
    if not config.CURRENT_ONLY:
        return chunks
    versioned = {chunk.title for chunk in chunks if chunk.status == "superseded"}
    wanted = requested_versions(query, {chunk.version for chunk in chunks if chunk.title in versioned})
    if wanted is None:
        return [chunk for chunk in chunks if chunk.status != "superseded"]
    keep = []
    for chunk in chunks:
        if chunk.title not in versioned:
            if chunk.status != "superseded":
                keep.append(chunk)
        elif chunk.version in wanted or ("superseded" in wanted and chunk.status == "superseded"):
            keep.append(chunk)
    return keep


def retrieve_top_k(query: str, chunks: list[Chunk], k: int | None = None) -> list[RetrievalResult]:
    k = config.TOP_K if k is None else k
    if k <= 0:
        raise ValueError("k must be > 0")

    candidates = searchable_chunks(chunks, query)
    scores = score_chunks(query, candidates)
    keys = sort_keys(query, candidates, scores)
    scored = [
        (key, RetrievalResult(chunk=chunk, score=score))
        for chunk, score, key in zip(candidates, scores, keys)
    ]
    filtered = [(key, item) for key, item in scored if item.score >= config.RETRIEVAL_MIN_SCORE]
    filtered.sort(key=lambda pair: (-pair[0], pair[1].chunk.chunk_id))
    return [item for _, item in filtered[:k]]
