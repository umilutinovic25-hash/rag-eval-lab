import pytest

from src import config, llm, rag
from src.chunking import Chunk


def make_chunk(chunk_id: str, text: str) -> Chunk:
    return Chunk(chunk_id=chunk_id, doc_id=chunk_id, title="T", version="2026", status="current", text=text)


CHUNKS = [
    make_chunk("a", "laptop replacement takes 5 business days"),
    make_chunk("b", "laptop accessories are ordered in the portal"),
    make_chunk("c", "laptop that does not start goes to the desk"),
]


@pytest.fixture
def rerank_mode(monkeypatch):
    monkeypatch.setattr(config, "RERANK", "llm")
    monkeypatch.setattr(config, "RERANK_CANDIDATES", 3)
    monkeypatch.setattr(config, "TOP_K", 2)


def judge(yes_ids):
    texts = {chunk.text for chunk in CHUNKS if chunk.chunk_id in yes_ids}
    return lambda question, passage: passage in texts


def test_rerank_keeps_only_passages_the_judge_accepts(rerank_mode, monkeypatch) -> None:
    monkeypatch.setattr(rag, "passage_answers", judge({"c"}))
    result = rag.build_grounded_answer("laptop", CHUNKS)
    assert result.refused is False
    assert result.citations == ["c"]


def test_rerank_refuses_when_judge_rejects_every_candidate(rerank_mode, monkeypatch) -> None:
    monkeypatch.setattr(rag, "passage_answers", judge(set()))
    result = rag.build_grounded_answer("laptop", CHUNKS)
    assert result.refused is True and result.citations == []


def test_rerank_ignores_score_thresholds(rerank_mode, monkeypatch) -> None:
    monkeypatch.setattr(config, "REFUSAL_THRESHOLD", 10.0)
    monkeypatch.setattr(rag, "passage_answers", judge({"a", "b", "c"}))
    assert len(rag.build_grounded_answer("laptop", CHUNKS).citations) == 2


@pytest.mark.parametrize(
    "top, judge_calls, refused",
    [(0.9, 0, False), (0.6, 3, False), (0.3, 0, True)],
    ids=["above-zone-trusts-retrieval", "inside-zone-asks-judge", "below-zone-refuses"],
)
def test_gray_zone_calls_judge_only_inside_zone(rerank_mode, monkeypatch, top, judge_calls, refused) -> None:
    monkeypatch.setattr(config, "RERANK", "llm-gray-zone")
    monkeypatch.setattr(config, "RERANK_GRAY_ZONE", (0.5, 0.7))
    monkeypatch.setattr(config, "SEMANTIC_CITATION_MIN_SCORE", 0.0)
    monkeypatch.setattr(rag.config, "RETRIEVAL_MODE", "semantic")
    scored = [rag.RetrievalResult(chunk=chunk, score=top - i * 0.01) for i, chunk in enumerate(CHUNKS)]
    monkeypatch.setattr(rag, "retrieve_top_k", lambda question, chunks, k=None: scored[:k])
    calls = []
    monkeypatch.setattr(rag, "passage_answers", lambda q, p: calls.append(p) or True)
    result = rag.build_grounded_answer("laptop", CHUNKS)
    assert len(calls) == judge_calls
    assert result.refused is refused


def test_generate_uses_cache_and_calls_model_once(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(llm, "CACHE_PATH", tmp_path / "llm.json")
    calls = []
    monkeypatch.setattr(llm, "request_generation", lambda m, p, n: calls.append(p) or " Yes \n")
    assert llm.generate("m", "prompt", 3) == "Yes"
    assert llm.generate("m", "prompt", 3) == "Yes"
    assert calls == ["prompt"]


@pytest.mark.parametrize("reply, expected", [("Yes", True), ("yes.", True), ("No.", False), ("", False)])
def test_passage_answers_parses_reply(monkeypatch, reply, expected) -> None:
    monkeypatch.setattr(llm, "generate", lambda model, prompt, max_tokens: reply)
    assert llm.passage_answers("q", "p") is expected


def test_uncached_prompt_without_ollama_raises_llm_error(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(llm, "CACHE_PATH", tmp_path / "llm.json")
    monkeypatch.setattr(llm, "OLLAMA_URL", "http://127.0.0.1:9/api/generate")
    monkeypatch.setattr(llm, "request_generation", REAL_REQUEST)
    with pytest.raises(llm.LLMError):
        llm.generate("m", "prompt", 3)


REAL_REQUEST = llm.request_generation  # saved at import, before conftest blocks the network
