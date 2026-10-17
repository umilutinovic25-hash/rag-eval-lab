from dataclasses import dataclass

from . import config
from .chunking import Chunk, build_chunks
from .corpus import load_corpus
from .llm import passage_answers, write_answer
from .retrieval import RetrievalResult, retrieve_top_k


REFUSAL_MESSAGE = "I do not have enough grounded evidence in the provided corpus to answer that question."


@dataclass(frozen=True)
class RagAnswer:
    answer: str
    citations: list[str]
    refused: bool
    retrieved: list[RetrievalResult]


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


def build_grounded_answer(question: str, chunks: list[Chunk]) -> RagAnswer:
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

    if config.ANSWER_MODE == "llm":
        answer = write_answer(question, [(item.chunk.chunk_id, item.chunk.text) for item in cited])
    else:
        supporting_points = [f"[{item.chunk.chunk_id}] {item.chunk.text}" for item in cited]
        answer = "Grounded response based on retrieved context:\n" + "\n".join(supporting_points)
    return RagAnswer(
        answer=answer,
        citations=[item.chunk.chunk_id for item in cited],
        refused=False,
        retrieved=results,
    )


def answer_question(question: str) -> RagAnswer:
    return build_grounded_answer(question, build_chunks(load_corpus()))
