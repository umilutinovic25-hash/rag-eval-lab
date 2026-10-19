import json

import pytest

from src import config, judge_calibration, llm, retrieval, retrieval_metrics
from src.chunking import Chunk


def chunk(chunk_id, text, title="Policy", doc="d1", status="current"):
    return Chunk(chunk_id, doc, title, "2026", status, text)


def test_bm25_prefers_rare_terms_and_handles_empty_input() -> None:
    chunks = [chunk("a", "the badge opens every door"), chunk("b", "the parking rules and the door"), chunk("c", "the the the")]
    scores = retrieval.bm25_scores("badge", chunks)
    assert scores[0] > scores[1] == scores[2] == 0.0
    assert retrieval.bm25_scores("badge", []) == []
    assert retrieval.bm25_scores("", chunks) == [0.0, 0.0, 0.0]


def test_bm25_idf_downweights_common_words() -> None:
    chunks = [chunk("a", "policy badge"), chunk("b", "policy parking"), chunk("c", "policy lunch")]
    common, rare = retrieval.bm25_scores("policy", chunks)[0], retrieval.bm25_scores("badge", chunks)[0]
    assert rare > common > 0


def test_headers_change_only_the_embedded_text(monkeypatch) -> None:
    c = chunk("a", "Never share passwords.", title="Passwords and access")
    assert retrieval.chunk_embedding_text(c) == "Never share passwords."
    monkeypatch.setattr(config, "CHUNK_HEADERS", True)
    assert retrieval.chunk_embedding_text(c) == "Passwords and access: Never share passwords."
    seen = []
    monkeypatch.setattr(retrieval, "embed", lambda texts: seen.extend(texts) or [[1.0, 0.0]] * len(texts))
    monkeypatch.setattr(config, "RETRIEVAL_MODE", "semantic")
    retrieval.semantic_scores("q", [c])
    assert seen == ["q", "Passwords and access: Never share passwords."]
    assert c.text == "Never share passwords."


def test_hybrid_bm25_orders_by_fusion_but_reports_cosine(monkeypatch) -> None:
    chunks = [chunk("a", "alpha only"), chunk("b", "badge door entrance")]
    vectors = {"badge": [1.0, 0.0], "alpha only": [0.9, 0.1], "badge door entrance": [0.7, 0.3]}
    monkeypatch.setattr(retrieval, "embed", lambda texts: [vectors[t] for t in texts])
    monkeypatch.setattr(config, "RETRIEVAL_MODE", "semantic")
    assert [r.chunk.chunk_id for r in retrieval.retrieve_top_k("badge", chunks, k=2)] == ["a", "b"]
    monkeypatch.setattr(config, "RETRIEVAL_MODE", "hybrid-bm25")
    monkeypatch.setattr(config, "HYBRID_WEIGHT", 0.2)
    results = retrieval.retrieve_top_k("badge", chunks, k=2)
    assert [r.chunk.chunk_id for r in results] == ["b", "a"]
    assert results[0].score == pytest.approx(0.7 / (0.7**2 + 0.3**2) ** 0.5, abs=1e-6)


def test_min_max_constant_input() -> None:
    assert retrieval.min_max([2.0, 2.0]) == [0.0, 0.0]
    assert retrieval.min_max([1.0, 3.0]) == [0.0, 1.0]


def test_fewshot_judge_uses_its_own_model_and_prompt(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(llm, "generate", lambda model, prompt, tokens: calls.append((model, prompt, tokens)) or "Yes.")
    monkeypatch.setattr(config, "RERANK_JUDGE", "fewshot")
    assert llm.passage_answers("Can I park here?", "Parking is not allowed.") is True
    model, prompt, tokens = calls[0]
    assert model == config.RERANK_FEWSHOT_MODEL and tokens == 3
    assert "Question: Can I park here?" in prompt and "Parking is not allowed." in prompt
    assert config.RERANK_FEWSHOT_MODEL.split(":")[0] not in config.GENERATION_MODEL


PASSAGES = [("a-0", "Unused budget does not carry over."), ("a-1", "Agree training with your manager.")]


@pytest.mark.parametrize("reply, expected", [
    ('{"answer": "No.", "sources": ["a-0"]}', "No. [a-0]"),
    ('```json\n{"answer": "Ask your manager.", "sources": ["a-1", "a-1"]}\n```', "Ask your manager. [a-1]"),
])
def test_json_answer_is_rendered_with_markers(monkeypatch, reply, expected) -> None:
    monkeypatch.setattr(config, "ANSWER_FORMAT", "json")
    monkeypatch.setattr(llm, "generate", lambda model, prompt, tokens: llm.GenerationText(reply, {"done_reason": "stop"}))
    text = llm.write_answer("q", PASSAGES)
    assert text == expected and text.metadata == {"done_reason": "stop"}


@pytest.mark.parametrize("reply", [
    "not json", '{"answer": "x"}', '{"answer": "x", "sources": []}', '{"answer": "x", "sources": ["zzz"]}',
    '{"answer": "x [a-0]", "sources": ["a-0"]}', '{"answer": "", "sources": ["a-0"]}',
    '{"answer": "x", "sources": ["a-0"], "extra": 1}',
])
def test_invalid_json_answer_is_returned_raw_so_the_fallback_triggers(monkeypatch, reply) -> None:
    from src import rag
    monkeypatch.setattr(config, "ANSWER_FORMAT", "json")
    monkeypatch.setattr(llm, "generate", lambda model, prompt, tokens: reply)
    text = llm.write_answer("q", PASSAGES)
    assert text == reply
    cited = [rag.RetrievalResult(chunk("a-0", PASSAGES[0][1]), 0.9)]
    assert rag.generation_issue(text, cited) is not None


def test_item_metrics_ranks_fact_chunks() -> None:
    item = {"id": "X", "category": "c", "expected_doc_ids": ["d1"], "expected_fact": "carry over"}
    order = [chunk("w", "other", doc="d2"), chunk("r", "It does not carry over.", doc="d1"), chunk("s", "more", doc="d1")]
    row = retrieval_metrics.item_metrics(item, order)
    assert row["first_fact_rank"] == 2 and row["mrr"] == 0.5
    assert row["doc_hit@1"] is False and row["doc_hit@2"] is True
    assert row["fact_recall@1"] == 0.0 and row["fact_recall@2"] == 1.0
    assert 0 < row["ndcg5"] < 1


def test_item_metrics_when_the_fact_is_missing() -> None:
    row = retrieval_metrics.item_metrics({"id": "X", "category": "c", "expected_doc_ids": ["d1"], "expected_fact": "zzz"},
                                         [chunk("a", "text")])
    assert row["first_fact_rank"] is None and row["mrr"] == 0.0 and row["fact_recall@5"] == 0.0


def test_calibration_rates_and_wilson_interval() -> None:
    pairs = [{"label": True}, {"label": True}, {"label": False}, {"label": False}]
    r = judge_calibration.rates(pairs, [True, False, False, True])
    assert (r["tp"], r["fn"], r["tn"], r["fp"], r["tpr"], r["tnr"]) == (1, 1, 1, 1, 0.5, 0.5)
    low, high = judge_calibration.wilson(1, 2)
    assert 0 < low < 0.5 < high < 1
    assert judge_calibration.wilson(0, 0) == [0.0, 0.0]


def test_calibration_labels_need_document_and_fact(monkeypatch) -> None:
    monkeypatch.setattr(judge_calibration, "ranked", lambda question, chunks: chunks[:2])
    monkeypatch.setattr(judge_calibration, "score_chunks", lambda q, c: [0.6] * len(c))
    monkeypatch.setattr(judge_calibration, "load_eval_set", lambda path: [
        {"id": "Q1", "question": "q", "expected_behaviour": "answer", "expected_doc_ids": ["hb-08"], "expected_fact": "does not carry over"},
        {"id": "Q2", "question": "r", "expected_behaviour": "refuse", "expected_doc_ids": [], "expected_fact": None}])
    pairs = judge_calibration.build_pairs(sets=("eval",), depth=2)
    positives = [p for p in pairs if p["label"]]
    assert {p["id"] for p in positives} <= {"Q1"} and all("does not carry over" in p["passage"].lower() for p in positives)
    assert all(not p["label"] for p in pairs if p["id"] == "Q2") and all(p["gray_zone"] for p in pairs)


def test_scratch_caches_never_touch_committed_files(tmp_path) -> None:
    from src import embeddings, scratch
    original = embeddings.CACHE_PATH, llm.CACHE_PATH
    try:
        scratch.use_scratch_caches(tmp_path)
        assert embeddings.CACHE_PATH.parent == tmp_path and llm.CACHE_PATH.parent == tmp_path
        assert json.loads((tmp_path / "embedding_cache.json").read_text())
    finally:
        embeddings.CACHE_PATH, llm.CACHE_PATH = original


@pytest.mark.parametrize("question, expected", [
    ("Is the old limit of 2 remote days still in force?", True), ("Can I bring a dog?", True),
    ("  does the company offer a pension plan?", True), ("May I work remotely?", True),
    ("How many days of leave do I get?", False), ("What is the dress code?", False),
    ("Where do I order a headset?", False), ("Isolation rules for laptops?", False),
])
def test_yes_no_question_detection(question, expected) -> None:
    assert llm.is_yes_no_question(question) is expected


@pytest.mark.parametrize("reply, accepted", [("Yes.", True), ("no", True), ("No, it is not.", True),
                                              ("Unknown", False), ("unknown.", False), ("I cannot say", False)])
def test_answerability_judge_accepts_yes_and_no_but_not_unknown(monkeypatch, reply, accepted) -> None:
    monkeypatch.setattr(llm, "generate", lambda model, prompt, tokens: reply)
    assert llm.answerability_judge("Is it so?", "It is so.") is accepted


def test_yes_no_question_judge_modes(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(llm, "base_passage_answers", lambda q, p: calls.append("base") or False)
    monkeypatch.setattr(llm, "answerability_judge", lambda q, p: calls.append("3way") or True)
    assert llm.passage_answers("Is it so?", "p") is False and calls == ["base"]  # disabled (conftest default)
    calls.clear()
    monkeypatch.setattr(config, "YESNO_QUESTION_JUDGE", "answerability")
    assert llm.passage_answers("Is it so?", "p") is True and calls == ["base", "3way"]
    calls.clear()
    monkeypatch.setattr(config, "YESNO_QUESTION_JUDGE", "answerability-only")
    assert llm.passage_answers("Is it so?", "p") is True and calls == ["3way"]
    calls.clear()
    assert llm.passage_answers("What is it?", "p") is False and calls == ["base"]  # not a yes/no question
    assert config.YESNO_QUESTION_MODEL.split(":")[0] not in config.GENERATION_MODEL
