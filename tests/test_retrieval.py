from src import config
from src.chunking import Chunk
from src.retrieval import retrieve_top_k, searchable_chunks


def make_chunk(chunk_id: str, text: str) -> Chunk:
    return Chunk(chunk_id=chunk_id, doc_id="d", title="T", version="2026", status="current", text=text)


def test_retrieve_top_k_orders_by_score_desc() -> None:
    chunks = [
        make_chunk("a", "rag retrieval citations evidence"),
        make_chunk("b", "weather forecast rain tomorrow"),
    ]
    results = retrieve_top_k("rag citations", chunks, k=2)
    assert results
    assert results[0].chunk.chunk_id == "a"


def test_retrieve_top_k_returns_empty_for_unrelated_query() -> None:
    chunks = [make_chunk("a", "vector database retrieval")]
    assert retrieve_top_k("basketball playoffs", chunks, k=2) == []


def test_ties_are_broken_by_chunk_id() -> None:
    chunks = [make_chunk("b", "leave policy"), make_chunk("a", "leave policy")]
    results = retrieve_top_k("leave", chunks, k=2)
    assert [r.chunk.chunk_id for r in results] == ["a", "b"]


def test_current_only_excludes_superseded_chunks(monkeypatch) -> None:
    old = Chunk("old", "d-old", "T", "2024", "superseded", "remote work policy")
    new = Chunk("new", "d-new", "T", "2026", "current", "remote work policy")
    monkeypatch.setattr(config, "CURRENT_ONLY", True)
    assert searchable_chunks([old, new]) == [new]
    monkeypatch.setattr(config, "CURRENT_ONLY", False)
    assert searchable_chunks([old, new]) == [old, new]


def test_historical_versions_follow_the_question(monkeypatch) -> None:
    old = Chunk("old", "d-old", "T", "2024", "superseded", "remote work policy")
    new = Chunk("new", "d-new", "T", "2026", "current", "remote work policy")
    other = Chunk("o", "d-o", "U", "2026", "current", "annual leave")
    chunks = [old, new, other]
    monkeypatch.setattr(config, "CURRENT_ONLY", True)
    monkeypatch.setattr(config, "HISTORICAL_VERSIONS", False)
    assert searchable_chunks(chunks, "What was the previous limit?") == [new, other]
    monkeypatch.setattr(config, "HISTORICAL_VERSIONS", True)
    assert searchable_chunks(chunks, "How many days can I work remotely?") == [new, other]
    assert searchable_chunks(chunks, "What was the previous limit?") == [old, other]
    assert searchable_chunks(chunks, "What did the 2024 policy allow?") == [old, other]
    assert searchable_chunks(chunks, "What does the 2026 policy allow?") == [new, other]
    assert searchable_chunks(chunks, "Before the 2026 update, what was allowed?") == [old, other]
    assert searchable_chunks(chunks, "What was the limit before the current policy?") == [old, other]
    assert searchable_chunks(chunks, "What was the 2022 limit?") == [other]
    assert searchable_chunks(chunks, "Is the old limit still valid now?") == [new, other]
    assert searchable_chunks(chunks, "How old must customers be?") == [new, other]


def test_past_only_mode_excludes_single_version_documents(monkeypatch) -> None:
    old = Chunk("old", "d-old", "T", "2024", "superseded", "remote work policy")
    new = Chunk("new", "d-new", "T", "2026", "current", "remote work policy")
    other = Chunk("o", "d-o", "U", "2026", "current", "annual leave")
    monkeypatch.setattr(config, "CURRENT_ONLY", True)
    monkeypatch.setattr(config, "HISTORICAL_VERSIONS", True)
    monkeypatch.setattr(config, "HISTORICAL_PAST_ONLY", True)
    assert searchable_chunks([old, new, other], "What was the previous leave policy?") == [old]
    assert searchable_chunks([old, new, other], "What did the 2024 policy allow?") == [old, other]
    assert searchable_chunks([old, new, other], "How many leave days do I get?") == [new, other]
