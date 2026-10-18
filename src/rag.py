from dataclasses import dataclass, field
import re

from . import config
from .chunking import Chunk, build_chunks
from .corpus import load_corpus
from .claim_checks import claim_risks, clauses
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
    trace: list[dict] = field(default_factory=list)


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


def expand_context(cited: list[RetrievalResult], chunks: list[Chunk], window: int, policy: str = "all") -> list[RetrievalResult]:
    if window <= 0:
        return cited
    if policy not in ("all", "references"):
        raise ValueError("Unknown context policy")
    expanded = {}
    groups = list(dict.fromkeys((r.chunk.doc_id, r.chunk.version, r.chunk.status) for r in cited))
    for group in groups:
        siblings = [c for c in chunks if (c.doc_id, c.version, c.status) == group]
        selected = {}
        for anchor in cited:
            if (anchor.chunk.doc_id, anchor.chunk.version, anchor.chunk.status) != group:
                continue
            index = next(i for i, c in enumerate(siblings) if c.chunk_id == anchor.chunk.chunk_id)
            selected[anchor.chunk.chunk_id] = anchor
            if policy == "references":
                if not re.search(r"\b(?:same|that|this)\s+(?:form|policy|procedure|process)\b", anchor.chunk.text, re.I):
                    continue
                neighbors = siblings[max(0, index-window):index]
            else:
                neighbors = siblings[max(0, index-window):index+window+1]
            for neighbor in neighbors:
                # Score is inherited for provenance only; neighbors are not reranked.
                selected[neighbor.chunk_id] = RetrievalResult(neighbor, anchor.score)
        for sibling in siblings:
            if sibling.chunk_id in selected:
                expanded[sibling.chunk_id] = selected[sibling.chunk_id]
    return list(expanded.values())


def generation_issue(text: str, cited: list[RetrievalResult]) -> str | None:
    """Structural and numeric checks only; no claim of semantic verification."""
    if getattr(text, "metadata", {}).get("done_reason") == "length":
        return "truncated_answer"
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
    by_id = {item.chunk.chunk_id: item.chunk.text for item in cited}
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        linked = re.findall(r"\[([^\[\]\n]+)\]", sentence)
        sources = [by_id[c] for c in linked] if linked else list(by_id.values())
        risks = claim_risks(sentence, sources)
        if risks:
            return risks[0]
    return None


def build_grounded_answer(question: str, chunks: list[Chunk]) -> RagAnswer:
    trace = []
    def refuse(reason, retrieved):
        trace.append({"stage": "decision", "reason": reason, "refused": True})
        return RagAnswer(answer=REFUSAL_MESSAGE, citations=[], refused=True, retrieved=retrieved, trace=trace)

    def record_retrieval(results):
        trace.append({"stage": "retrieval", "candidates": [{"chunk_id": r.chunk.chunk_id, "score": r.score} for r in results]})

    if not question.strip():
        return refuse("empty_question", [])
    if config.RERANK == "llm-gray-zone" and config.RETRIEVAL_MODE not in ("semantic", "hybrid"):
        raise ValueError("llm-gray-zone requires semantic or hybrid cosine scores; use the offline profile for lexical.")
    if config.RERANK in ("llm", "llm-gray-zone"):
        candidates = retrieve_top_k(question, chunks, k=config.RERANK_CANDIDATES)
        record_retrieval(candidates)
        top = candidates[0].score if candidates else 0.0
        low, high = config.RERANK_GRAY_ZONE
        if config.RERANK == "llm-gray-zone" and top >= high:
            results = candidates[: config.TOP_K]
            cited = select_citations(results)
            trace.append({"stage": "decision", "reason": "above_gray_zone"})
        elif config.RERANK == "llm-gray-zone" and top < low:
            return refuse("below_gray_zone", candidates[: config.TOP_K])
        else:
            results = []
            for item in candidates:
                accepted = passage_answers(question, item.chunk.text)
                trace.append({"stage": "judge", "chunk_id": item.chunk.chunk_id, "accepted": accepted})
                if accepted:
                    results.append(item)
                    if len(results) == config.TOP_K:
                        break
            if not results:
                return refuse("no_accepted_candidate", candidates[: config.TOP_K])
            cited = results
    else:
        results = retrieve_top_k(question, chunks)
        record_retrieval(results)
        if not results or results[0].score < refusal_threshold():
            return refuse("below_refusal_threshold", results)
        cited = select_citations(results)

    anchors = [r.chunk.chunk_id for r in cited]
    cited = expand_context(cited, chunks, config.CONTEXT_NEIGHBORS, config.CONTEXT_POLICY)
    if config.CONTEXT_NEIGHBORS:
        trace.append({"stage": "context", "anchors": anchors, "expanded": [r.chunk.chunk_id for r in cited], "neighbor_scores": "inherited; not retrieval scores"})
    fallback_reason = None
    if config.ANSWER_MODE == "llm":
        try:
            answer = write_answer(question, [(item.chunk.chunk_id, item.chunk.text) for item in cited])
            trace.append({"stage": "generation", "text": str(answer), "metadata": getattr(answer, "metadata", {"done_reason": "unknown"})})
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
        trace=trace + [{"stage": "decision", "refused": False, "citations": [r.chunk.chunk_id for r in cited], "fallback": fallback_reason}],
    )


def answer_question(question: str) -> RagAnswer:
    return build_grounded_answer(question, build_chunks(load_corpus()))
