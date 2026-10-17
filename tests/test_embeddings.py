import pytest

from src import config, embeddings, rag, retrieval
from src.chunking import Chunk


def make_chunk(chunk_id: str, text: str) -> Chunk:
    return Chunk(chunk_id=chunk_id, doc_id=chunk_id, title="T", version="2026", status="current", text=text)


FAKE_VECTORS = {
    "laptop question": [1.0, 0.0],
    "laptop text": [0.9, 0.1],
    "parking text": [0.0, 1.0],
}


@pytest.fixture
def semantic_mode(monkeypatch):
    monkeypatch.setattr(config, "RETRIEVAL_MODE", "semantic")
    monkeypatch.setattr(retrieval, "embed", lambda texts: [FAKE_VECTORS[t] for t in texts])


def test_cosine_basic_values() -> None:
    assert embeddings.cosine([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert embeddings.cosine([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    assert embeddings.cosine([0.0, 0.0], [1.0, 0.0]) == 0.0


def test_cache_key_depends_on_model() -> None:
    assert embeddings.cache_key("text", "a") != embeddings.cache_key("text", "b")


def test_embed_uses_cache_and_requests_only_missing(tmp_path, monkeypatch) -> None:
    path = tmp_path / "cache.json"
    monkeypatch.setattr(embeddings, "CACHE_PATH", path)
    embeddings.save_cache({embeddings.cache_key("known"): [1.0, 0.0]}, path)
    requested = []
    monkeypatch.setattr(embeddings, "request_embeddings", lambda texts: requested.extend(texts) or [[0.0, 1.0]] * len(texts))
    assert embeddings.embed(["known", "new", "new"]) == [[1.0, 0.0], [0.0, 1.0], [0.0, 1.0]]
    assert requested == ["new"]
    assert embeddings.cache_key("new") in embeddings.load_cache(path)


def test_semantic_mode_ranks_by_cosine(semantic_mode) -> None:
    chunks = [make_chunk("b", "parking text"), make_chunk("a", "laptop text")]
    results = retrieval.retrieve_top_k("laptop question", chunks, k=2)
    assert [r.chunk.chunk_id for r in results] == ["a"]


def test_semantic_mode_uses_semantic_refusal_threshold(semantic_mode, monkeypatch) -> None:
    chunks = [make_chunk("a", "laptop text")]
    monkeypatch.setattr(config, "SEMANTIC_REFUSAL_THRESHOLD", 0.999)
    assert rag.build_grounded_answer("laptop question", chunks).refused is True
    monkeypatch.setattr(config, "SEMANTIC_REFUSAL_THRESHOLD", 0.5)
    assert rag.build_grounded_answer("laptop question", chunks).citations == ["a"]


def test_unknown_retrieval_mode_raises(monkeypatch) -> None:
    monkeypatch.setattr(config, "RETRIEVAL_MODE", "magic")
    with pytest.raises(ValueError):
        retrieval.retrieve_top_k("q", [make_chunk("a", "text")], k=1)
