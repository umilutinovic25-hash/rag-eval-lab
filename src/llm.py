"""Local LLM calls through Ollama, cached on disk so eval runs stay offline and deterministic."""

import hashlib
import json
import re
import urllib.request
import time

from . import config, operation, model_identity
from .claim_checks import clauses
from .embeddings import CACHE_PATH as EMBEDDING_CACHE_PATH, EmbeddingError, load_cache, save_cache


CACHE_PATH = EMBEDDING_CACHE_PATH.with_name("llm_cache.json")
OLLAMA_URL = "http://localhost:11434/api/generate"
ACCEPT_WORDS = {"yes", "relevant"}
WORD_RE = re.compile(r"[a-z0-9]+(?:['’][a-z]+)?")
NEGATIONS = {"never", "not", "no", "cannot"}


class LLMError(RuntimeError):
    """Raised when a prompt is not cached and Ollama cannot answer it."""


class GenerationText(str):
    """Text compatible with historical caches, carrying observed completion metadata."""
    def __new__(cls, text: str, metadata: dict | None = None):
        obj = super().__new__(cls, text)
        obj.metadata = metadata or {"done_reason": "unknown", "provenance": "historical_or_unrecorded"}
        return obj


def metadata_path():
    return CACHE_PATH.with_name(CACHE_PATH.stem + "-metadata.json")


def cache_key(model: str, prompt: str, max_tokens: int) -> str:
    legacy=hashlib.sha256(f"{model}\n{max_tokens}\n{prompt}".encode("utf-8")).hexdigest()
    return model_identity.key(legacy,model,{'temperature':0,'seed':7,'num_predict':max_tokens})


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
        with urllib.request.urlopen(request, timeout=operation.timeout(120)) as response:
            body = json.load(response)
            text = body["response"]
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise LLMError(f"Uncached prompt needs Ollama with model {model!r} at {OLLAMA_URL} ({error}).") from error
    operation.check()
    if not isinstance(text, str) or not text.strip():
        raise LLMError(f"Ollama returned no text for model {model!r}.")
    return GenerationText(text, {k: body.get(k) for k in ("done_reason", "done", "model", "eval_count", "prompt_eval_count", "total_duration")})


def generate(model: str, prompt: str, max_tokens: int) -> str:
    operation.check()
    try:
        cache = load_cache(CACHE_PATH)
        metadata = load_cache(metadata_path())
    except EmbeddingError as error:
        raise LLMError(str(error)) from error
    key = cache_key(model, prompt, max_tokens)
    if key not in cache:
        before=model_identity.require_live(model)
        started=time.perf_counter()
        try:
            response = request_generation(model, prompt, max_tokens)
        except Exception:
            operation.record('llm',seconds=time.perf_counter()-started)
            raise
        operation.record('llm',metadata=getattr(response,'metadata',{}),seconds=time.perf_counter()-started)
        model_identity.verify(model,before)
        cache[key] = response.strip()
        metadata[key] = getattr(response, "metadata", {"done_reason": "unknown", "provenance": "unrecorded"})
        save_cache(cache, CACHE_PATH)
        save_cache(metadata, metadata_path())
    else:
        operation.record('llm',cached=True)
    text = cache[key]
    if not isinstance(text, str) or not text.strip():
        raise LLMError("Cached LLM response must be nonempty text.")
    return GenerationText(text, metadata.get(key))


def span_is_in_passage(span: str, passage: str) -> bool:
    """Match contiguous source tokens, preserving a source sentence's negation.

    This checks copied evidence, not relevance or semantic entailment.
    """
    words = WORD_RE.findall(span.casefold().replace("’", "'"))
    if not words or words[0] == "none":
        return False
    has_negative = lambda tokens: any(t in NEGATIONS or t.endswith("n't") for t in tokens)
    for sentence in clauses(passage):
        source = WORD_RE.findall(sentence.casefold().replace("’", "'"))
        for start in range(len(source) - len(words) + 1):
            if source[start : start + len(words)] == words:
                if not has_negative(source) or has_negative(words):
                    return True
    return False


def span_judge(question: str, passage: str) -> bool:
    span = generate(config.RERANK_MODEL, config.RERANK_SPAN_PROMPT.format(question=question, passage=passage), 40)
    return span_is_in_passage(span, passage)


def yesno_judge(question: str, passage: str, model: str, prompt: str | None = None) -> bool:
    reply = generate(model, (prompt or config.RERANK_PROMPT).format(question=question, passage=passage), 3)
    words = reply.lower().split()
    return bool(words) and words[0].strip(".,!:") in ACCEPT_WORDS


def structured_judge(question: str, passage: str) -> bool:
    response = generate(config.RERANK_MODEL, config.RERANK_STRUCTURED_PROMPT.format(question=question, passage=passage), 160)
    if getattr(response, "metadata", {}).get("done_reason") == "length":
        return False
    text = response.strip()
    wrapped = re.fullmatch(r"```(?:json)?\s*\n(.*)\n```", text, re.S | re.I)
    if wrapped:
        text = wrapped.group(1)
    try:
        decision = json.loads(text)
    except (ValueError, TypeError):
        return False
    if not isinstance(decision, dict) or set(decision) != {"status", "evidence"}:
        return False
    if decision["status"] not in ("supported", "contradicted"):
        return False
    evidence = decision["evidence"]
    return isinstance(evidence, list) and bool(evidence) and all(
        isinstance(span, str) and span_is_in_passage(span, passage) for span in evidence
    )


YES_NO_START = re.compile(r"\s*(?:is|are|am|was|were|do|does|did|can|could|may|might|will|would|shall|should|must|have|has|had)\b", re.I)


def is_yes_no_question(question: str) -> bool:
    return bool(YES_NO_START.match(question))


def answerability_judge(question: str, passage: str, model: str | None = None, prompt: str | None = None) -> bool:
    reply = generate(model or config.YESNO_QUESTION_MODEL, (prompt or config.YESNO_QUESTION_PROMPT).format(question=question, passage=passage), 3)
    words = reply.lower().split()
    return bool(words) and words[0].strip(".,!:") in ("yes", "no")


def passage_answers(question: str, passage: str) -> bool:
    if config.YESNO_QUESTION_JUDGE and is_yes_no_question(question):
        if config.YESNO_QUESTION_JUDGE == "answerability-only":
            return answerability_judge(question, passage)
        return base_passage_answers(question, passage) or answerability_judge(question, passage)
    return base_passage_answers(question, passage)


def base_passage_answers(question: str, passage: str) -> bool:
    if config.RERANK_JUDGE == "structured":
        return structured_judge(question, passage)
    if config.RERANK_JUDGE == "fewshot":
        return yesno_judge(question, passage, config.RERANK_FEWSHOT_MODEL, config.RERANK_FEWSHOT_PROMPT)
    if config.RERANK_JUDGE == "span":
        return span_judge(question, passage)
    if config.RERANK_JUDGE == "either":
        return span_judge(question, passage) or yesno_judge(question, passage, config.RERANK_YESNO_MODEL)
    return yesno_judge(question, passage, config.RERANK_MODEL)


def render_json_answer(response: str, passages: list[tuple[str, str]]) -> str:
    """Turn a JSON reply into the usual text with [id] markers; anything invalid is returned raw so that the
    existing structural checks reject it and the extractive fallback is used."""
    text = response.strip()
    wrapped = re.fullmatch(r"```(?:json)?\s*\n(.*)\n```", text, re.S | re.I)
    if wrapped:
        text = wrapped.group(1)
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return response
    if not isinstance(data, dict) or set(data) != {"answer", "sources"}:
        return response
    answer, sources = data["answer"], data["sources"]
    ids = {chunk_id for chunk_id, _ in passages}
    if not isinstance(answer, str) or not answer.strip() or "[" in answer or "]" in answer:
        return response
    if not isinstance(sources, list) or not sources or not all(isinstance(i, str) and i in ids for i in sources):
        return response
    rendered = answer.strip() + " " + "".join(f"[{i}]" for i in dict.fromkeys(sources))
    return GenerationText(rendered, getattr(response, "metadata", None))


def write_answer(question: str, passages: list[tuple[str, str]]) -> str:
    listed = "\n".join(f"[{chunk_id}] {text}" for chunk_id, text in passages)
    if config.ANSWER_FORMAT == "json":
        prompt = config.GENERATION_JSON_PROMPT.format(passages=listed, question=question)
        return render_json_answer(generate(config.GENERATION_MODEL, prompt, 160), passages)
    prompt = config.GENERATION_PROMPT.format(passages=listed, question=question)
    return generate(config.GENERATION_MODEL, prompt, 80)
