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


@pytest.mark.parametrize(
    "span, accepted",
    [
        ("reserved through facilities app", True),
        ("Parking is limited: spaces are shared", True),
        ("NONE", False),
        ("", False),
        ("book it with your manager in the HR portal", False),
    ],
    ids=["copied", "copied-with-punctuation", "none", "empty", "invented-evidence"],
)
def test_span_judge_accepts_only_evidence_copied_from_passage(monkeypatch, span, accepted) -> None:
    passage = "Parking is limited: spaces are shared and reserved through facilities app, first come, first served."
    monkeypatch.setattr(config, "RERANK_JUDGE", "span")
    monkeypatch.setattr(llm, "generate", lambda model, prompt, max_tokens: span)
    assert llm.passage_answers("How do I reserve a car space?", passage) is accepted


def test_uncached_prompt_without_ollama_raises_llm_error(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(llm, "CACHE_PATH", tmp_path / "llm.json")
    monkeypatch.setattr(llm, "OLLAMA_URL", "http://127.0.0.1:9/api/generate")
    monkeypatch.setattr(llm, "request_generation", REAL_REQUEST)
    with pytest.raises(llm.LLMError):
        llm.generate("m", "prompt", 3)


REAL_REQUEST = llm.request_generation  # saved at import, before conftest blocks the network


@pytest.mark.parametrize("which", ["eval", "holdout", "test"])
def test_committed_caches_cover_shipped_config_offline(monkeypatch, which) -> None:
    """The shipped config (semantic + gray-zone judge + LLM answers) must run both sets from the committed caches."""
    from src.eval_runner import run_eval
    from src.holdout_runner import run_holdout

    monkeypatch.setattr(config, "RETRIEVAL_MODE", "semantic")
    monkeypatch.setattr(config, "RERANK", "llm-gray-zone")
    monkeypatch.setattr(config, "ANSWER_MODE", "llm")
    from src.holdout_runner import TEST_SET_PATH

    run = {"eval": run_eval, "holdout": run_holdout, "test": lambda: run_holdout(TEST_SET_PATH)}[which]()
    assert run["summary"]["passed"] == {"eval": 12, "holdout": 33, "test": 22}[which]


def test_llm_answer_mode_keeps_citations_and_uses_model_text(rerank_mode, monkeypatch) -> None:
    monkeypatch.setattr(config, "RERANK", None)
    baseline = rag.build_grounded_answer("laptop replacement", CHUNKS)
    monkeypatch.setattr(config, "ANSWER_MODE", "llm")
    seen = []
    monkeypatch.setattr(rag, "write_answer", lambda q, passages: seen.extend(passages) or "It takes 5 business days [a].")
    result = rag.build_grounded_answer("laptop replacement", CHUNKS)
    assert result.answer == "It takes 5 business days [a]."
    assert result.citations == baseline.citations
    assert [chunk_id for chunk_id, _ in seen] == baseline.citations


def test_answer_quality_scores_fact_and_markers() -> None:
    from src.answer_quality import score_answer

    assert score_answer("Up to 5 business days [hb-01-chunk-1].", ["hb-01-chunk-1"], "5 business days") == {
        "fact_in_answer": True, "markers_valid": True,
    }
    assert score_answer("Five days [hb-09-chunk-0].", ["hb-01-chunk-1"], "5 business days") == {
        "fact_in_answer": False, "markers_valid": False,
    }
    assert score_answer("Five days.", ["hb-01-chunk-1"], "5 business days")["markers_valid"] is False
