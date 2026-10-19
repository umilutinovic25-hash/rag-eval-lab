from dataclasses import dataclass, field
import re
import time

from . import config, operation
from .chunking import Chunk, build_chunks
from .corpus import load_corpus
from .claim_checks import claim_risks, clauses
from .llm import LLMError, is_yes_no_question, passage_answers, passage_verdict, write_answer
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
    disposition: str = 'answer'
    clarification: list[str] = field(default_factory=list)


def citation_min_score() -> float | None:
    if config.RETRIEVAL_MODE in config.COSINE_MODES:
        return config.SEMANTIC_CITATION_MIN_SCORE
    return config.CITATION_MIN_SCORE


def select_citations(results: list[RetrievalResult]) -> list[RetrievalResult]:
    min_score = citation_min_score()
    if min_score is None or not results:
        return results
    return [results[0]] + [item for item in results[1:] if item.score >= min_score]


def refusal_threshold() -> float:
    if config.RETRIEVAL_MODE in config.COSINE_MODES:
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
                if not re.search(r"\b(?:(?:same|that|this)\s+(?:form|policy|procedure|process)|(?:isti|taj|ovaj)\s+(?:taj\s+)?(?:formular|obrazac|politika|procedura|postupak|proces))\b", anchor.chunk.text, re.I):
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


def generation_issue(text: str, cited: list[RetrievalResult], question: str = "") -> str | None:
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
    if config.NUMBERS_FROM_QUESTION:
        source += " " + question
    if not set(re.findall(r"\d+(?:[.:]\d+)*", body)) <= set(re.findall(r"\d+(?:[.:]\d+)*", source)):
        return "unsupported_number"
    by_id = {item.chunk.chunk_id: item.chunk.text for item in cited}
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        linked = re.findall(r"\[([^\[\]\n]+)\]", sentence)
        sources = [by_id[c] for c in linked] if linked else list(by_id.values())
        risks = claim_risks(sentence, sources, question if config.NUMBERS_FROM_QUESTION else "")
        if risks:
            return risks[0]
    return None


def build_grounded_answer(question: str, chunks: list[Chunk]) -> RagAnswer:
    operation.progress('retrieval', 'Pretražujem odlomke priručnika.')
    started = time.perf_counter()
    trace = []
    def refuse(reason, retrieved):
        trace.append({"stage": "stage_timing", "total_s": round(time.perf_counter() - started, 3)})
        trace.append({"stage": "decision", "reason": reason, "refused": True})
        return RagAnswer(answer=REFUSAL_MESSAGE, citations=[], refused=True, retrieved=retrieved, trace=trace)

    def record_retrieval(results):
        trace.append({"stage": "retrieval", "candidates": [{"chunk_id": r.chunk.chunk_id, "score": r.score} for r in results]})

    def version_intent():
        return config.VERSION_CONTEXT and bool(re.search(
            r"\b(current|latest|active|superseded|still|now|in force|20\d{2})\b", question, re.I))

    def judge_context(chunk):
        if not version_intent():
            return chunk.text
        return f"Document: {chunk.title}; version: {chunk.version}; status: {chunk.status}.\n{chunk.text}"

    def relevant(selected):
        from .llm import evidence_supports
        try:
            accepted = evidence_supports(question, [
                {"title": r.chunk.title, "version": r.chunk.version, "status": r.chunk.status, "text": r.chunk.text}
                for r in selected])
        except LLMError:
            accepted = False
        trace.append({"stage": "evidence_relevance", "accepted": accepted,
                      "chunks": [r.chunk.chunk_id for r in selected]})
        return accepted

    def jev_filter(selected):
        from .jev import JevError, classify
        operation.progress('judge', 'Proveravam izvore preko TypeSafe servisa.')
        try:
            decisions = classify(question, [r.chunk for r in selected])
        except JevError as error:
            trace.append({"stage": "jev_error", "code": error.code, "model": config.JEV_MODEL})
            return None
        accepted = []
        for item, decision in zip(selected, decisions):
            trace.append({"stage": "jev", "chunk_id": item.chunk.chunk_id,
                          "model": decision.model, "label": decision.label,
                          "probability": decision.probability, "confidence": decision.confidence,
                          "accepted": decision.accepted, "cached": decision.cached})
            if decision.accepted:
                accepted.append(item)
        return accepted

    if not question.strip():
        return refuse("empty_question", [])
    if config.INJECTION_GUARDS:
        from .evidence import meta_request, suspicious as explicit_injection
        if meta_request(question) and not (config.EVIDENCE_RULES_ENABLED and explicit_injection(question)):
            return refuse("assistant_meta_request", [])
    if config.EVIDENCE_RULES_ENABLED:
        from .evidence import suspicious, select
        if suspicious(question):
            return refuse('untrusted_instruction', [])
        chunks = [c for c in chunks if not suspicious(c.text)]
        if re.fullmatch(r'\s*(?:how (?:do|can) i submit (?:a |the )?request|help|request|kako (?:da )?(?:podnesem|posaljem) zahtev|pomoc)\s*[?.!]*', question, re.I):
            topics = list(dict.fromkeys(c.title for c in chunks if c.status == 'current'))[:8]
            return RagAnswer('Which policy or type of request do you mean?', [], True, [], trace=[{'stage':'decision','reason':'ambiguous_request'}], disposition='clarification', clarification=topics)
        evidence = select(question, chunks)
        if evidence:
            text, selected, rule = evidence
            if config.JEV_ENABLED:
                checked = jev_filter(selected)
                if checked is None:
                    return refuse("jev_unavailable", selected)
                if len(checked) != len(selected):
                    return refuse("jev_insufficient_evidence", selected)
            if config.EVIDENCE_RELEVANCE and config.ANSWER_MODE == "llm" and not relevant(selected):
                return refuse("evidence_missing_subject", selected)
            return RagAnswer(text, [r.chunk.chunk_id for r in selected], False, selected,
                             trace=trace + [{'stage':'evidence','rule':rule,'score_kind':'lexical overlap, not cosine'}], disposition='limited' if rule=='separate_policy_limit' else 'answer')
    if config.RERANK == "llm-gray-zone" and config.RETRIEVAL_MODE not in config.COSINE_MODES:
        raise ValueError("llm-gray-zone requires semantic or hybrid cosine scores; use the offline profile for lexical.")
    if config.JEV_ENABLED:
        candidates = retrieve_top_k(question, chunks, k=config.RERANK_CANDIDATES)
        record_retrieval(candidates)
        accepted = jev_filter(candidates)
        if accepted is None:
            return refuse("jev_unavailable", candidates[:config.TOP_K])
        if not accepted:
            return refuse("jev_insufficient_evidence", candidates[:config.TOP_K])
        results = accepted[:config.TOP_K]
        cited = results
    elif config.RERANK in ("llm", "llm-gray-zone"):
        candidates = retrieve_top_k(question, chunks, k=config.RERANK_CANDIDATES)
        record_retrieval(candidates)
        top = candidates[0].score if candidates else 0.0
        low, high = config.RERANK_GRAY_ZONE
        if config.RERANK == "llm-gray-zone" and top >= high:
            results = candidates[: config.TOP_K]
            cited = select_citations(results)
            trace.append({"stage": "decision", "reason": "above_gray_zone"})
        elif config.RERANK == "llm-gray-zone" and top < low and not version_intent():
            return refuse("below_gray_zone", candidates[: config.TOP_K])
        else:
            results = []
            for item in candidates:
                operation.progress('judge', f'Proveravam relevantnost odlomka {candidates.index(item)+1}/{len(candidates)}.')
                accepted = passage_answers(question, judge_context(item.chunk))
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

    selected_at = time.perf_counter()
    anchors = [r.chunk.chunk_id for r in cited]
    cited = expand_context(cited, chunks, config.CONTEXT_NEIGHBORS, config.CONTEXT_POLICY)
    if config.CONTEXT_NEIGHBORS:
        trace.append({"stage": "context", "anchors": anchors, "expanded": [r.chunk.chunk_id for r in cited], "neighbor_scores": "inherited; not retrieval scores"})
    if config.JEV_ENABLED and [r.chunk.chunk_id for r in cited] != anchors:
        checked = jev_filter(cited)
        if checked is None:
            return refuse("jev_unavailable", results)
        if not checked:
            return refuse("jev_insufficient_evidence", results)
        cited = checked
    if config.EVIDENCE_RELEVANCE and config.ANSWER_MODE == "llm" and not relevant(cited):
        return refuse("evidence_missing_subject", results)
    fallback_reason = None
    if config.ANSWER_MODE == "llm":
        operation.progress('generation', 'Pripremam odgovor iz odabranih izvora.')
        try:
            answer = write_answer(question, [(item.chunk.chunk_id, item.chunk.text) for item in cited])
            trace.append({"stage": "generation", "text": str(answer), "metadata": getattr(answer, "metadata", {"done_reason": "unknown"})})
            fallback_reason = generation_issue(answer, cited, question)
            if not fallback_reason and config.INJECTION_GUARDS:
                from .evidence import language_mismatch
                if language_mismatch(question, answer):
                    fallback_reason = "language_mismatch"
            if not fallback_reason and config.POLARITY_CHECK and is_yes_no_question(question):
                lead = re.match(r"\s*(yes|no)\b", answer, re.I)
                if lead and passage_verdict(question, " ".join(item.chunk.text for item in cited)) == {"yes": "no", "no": "yes"}[lead[1].lower()]:
                    fallback_reason = "polarity_conflict"
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
        trace=trace + [{"stage": "stage_timing", "retrieval_and_judging_s": round(selected_at - started, 3),
                        "generation_s": round(time.perf_counter() - selected_at, 3), "total_s": round(time.perf_counter() - started, 3)},
                       {"stage": "decision", "refused": False, "citations": [r.chunk.chunk_id for r in cited], "fallback": fallback_reason}],
    )


def answer_question(question: str) -> RagAnswer:
    return build_grounded_answer(question, build_chunks(load_corpus()))
