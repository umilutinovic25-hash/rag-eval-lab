from src.chunking import Chunk
from src.retrieval import retrieve_top_k


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
