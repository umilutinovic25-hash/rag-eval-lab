from dataclasses import dataclass
import re

from . import config
from .chunking import Chunk, build_chunks
from .corpus import load_corpus
from .llm import LLMError, passage_answers, write_answer
from .retrieval import RetrievalResult, retrieve_top_k


QUOTE_PREFIX = "Source ["
REFUSAL_MESSAGE = "I do not have enough grounded evidence in the provided corpus to answer that question."


@dataclass(frozen=True)
class RagAnswer:
    answer: str
    citations: list[str]
    refused: bool
    retrieved: list[RetrievalResult]
    generation_fallback_reason: str | None = None


def citation_min_score() -> float | None:
    if config.RETRIEVAL_MODE in ("semantic", "hybrid"):
        return config.SEMANTIC_CITATION_MIN_SCORE
    return config.CITATION_MIN_SCORE


def select_citations(results: list[RetrievalResult]) -> list[RetrievalResult]:
    min_score = citation_min_score()
    if min_score is None or not results:
        return results
    return [results[0]] + [item for item in results[1:] if item.score >= min_score]


def refusal_threshold() -> float:
    if config.RETRIEVAL_MODE in ("semantic", "hybrid"):
        return config.SEMANTIC_REFUSAL_THRESHOLD
    return config.REFUSAL_THRESHOLD


def extractive_answer(cited: list[RetrievalResult]) -> str:
    return "Grounded response based on retrieved context:\n" + "\n".join(
        f"[{item.chunk.chunk_id}] {item.chunk.text}" for item in cited
    )


def generation_issue(text: str, cited: list[RetrievalResult]) -> str | None:
    """Structural and numeric checks only; no claim of semantic verification."""
    if not isinstance(text, str) or not text.strip():
        return "empty_answer"
    if any(line.lstrip().startswith(QUOTE_PREFIX) for line in text.splitlines()):
        return "generated_source_line"
    markers = re.findall(r"\[([^\[\]\n]+)\]", text)
    body = re.sub(r"\[[^\[\]\n]+\]", "", text)
    if "[" in body or "]" in body:
        return "malformed_marker"
    if not markers or not set(markers) <= {item.chunk.chunk_id for item in cited}:
        return "invalid_marker"
    source = " ".join(item.chunk.text for item in cited)
    if not set(re.findall(r"\d+(?:[.:]\d+)*", body)) <= set(re.findall(r"\d+(?:[.:]\d+)*", source)):
        return "unsupported_number"
    return None


def build_grounded_answer(question: str, chunks: list[Chunk]) -> RagAnswer:
    if not question.strip():
        return RagAnswer(answer=REFUSAL_MESSAGE, citations=[], refused=True, retrieved=[])
    if config.RERANK == "llm-gray-zone" and config.RETRIEVAL_MODE not in ("semantic", "hybrid"):
        raise ValueError("llm-gray-zone requires semantic or hybrid cosine scores; use the offline profile for lexical.")
    if config.RERANK in ("llm", "llm-gray-zone"):
        candidates = retrieve_top_k(question, chunks, k=config.RERANK_CANDIDATES)
        top = candidates[0].score if candidates else 0.0
        low, high = config.RERANK_GRAY_ZONE
        if config.RERANK == "llm-gray-zone" and top >= high:
            results = candidates[: config.TOP_K]
            cited = select_citations(results)
        elif config.RERANK == "llm-gray-zone" and top < low:
            return RagAnswer(answer=REFUSAL_MESSAGE, citations=[], refused=True, retrieved=candidates[: config.TOP_K])
        else:
            results = [item for item in candidates if passage_answers(question, item.chunk.text)][: config.TOP_K]
            if not results:
                return RagAnswer(answer=REFUSAL_MESSAGE, citations=[], refused=True, retrieved=candidates[: config.TOP_K])
            cited = results
    else:
        results = retrieve_top_k(question, chunks)
        if not results or results[0].score < refusal_threshold():
            return RagAnswer(answer=REFUSAL_MESSAGE, citations=[], refused=True, retrieved=results)
        cited = select_citations(results)

    fallback_reason = None
    if config.ANSWER_MODE == "llm":
        try:
            answer = write_answer(question, [(item.chunk.chunk_id, item.chunk.text) for item in cited])
            fallback_reason = generation_issue(answer, cited)
        except LLMError:
            fallback_reason = "generation_error"
        if fallback_reason:
            answer = extractive_answer(cited)
        elif config.ANSWER_QUOTES:
            answer += "".join(f'\n{QUOTE_PREFIX}{item.chunk.chunk_id}]: "{item.chunk.text}"' for item in cited)
    else:
        answer = extractive_answer(cited)
    return RagAnswer(
        answer=answer,
        citations=[item.chunk.chunk_id for item in cited],
        refused=False,
        retrieved=results,
        generation_fallback_reason=fallback_reason,
    )


def answer_question(question: str) -> RagAnswer:
    return build_grounded_answer(question, build_chunks(load_corpus()))
