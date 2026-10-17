import io
import json

import pytest

from src import config, embeddings, rag, retrieval

REAL_REQUEST = embeddings.request_embeddings  # saved before conftest blocks the network
from src.chunking import Chunk


def make_chunk(chunk_id: str, text: str) -> Chunk:
    return Chunk(chunk_id=chunk_id, doc_id=chunk_id, title="T", version="2026", status="current", text=text)


FAKE_VECTORS = {
    "laptop question": [1.0, 0.0],
    "laptop text": [0.9, 0.1],
    "parking text": [0.0, 1.0],
    "alpha": [0.9, 0.1],
    "laptop question": [1.0, 0.0],
    "beta gamma": [0.7, 0.3],
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


def test_hybrid_mode_orders_by_rrf_but_reports_cosine(semantic_mode, monkeypatch) -> None:
    monkeypatch.setattr(retrieval, "embed", lambda texts: [FAKE_VECTORS.get(t, [0.8, 0.2]) for t in texts])
    chunks = [make_chunk("c", "beta gamma"), make_chunk("a", "alpha"), make_chunk("b", "laptop question words")]
    semantic = retrieval.retrieve_top_k("laptop question", chunks, k=2)
    assert [r.chunk.chunk_id for r in semantic] == ["a", "b"]
    monkeypatch.setattr(config, "RETRIEVAL_MODE", "hybrid")
    hybrid = retrieval.retrieve_top_k("laptop question", chunks, k=2)
    assert [r.chunk.chunk_id for r in hybrid] == ["b", "a"]
    assert hybrid[0].score == pytest.approx(embeddings.cosine([1.0, 0.0], [0.8, 0.2]))


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


def test_corrupt_cache_raises_embedding_error(tmp_path) -> None:
    path = tmp_path / "cache.json"
    path.write_text("{truncated", encoding="utf-8")
    with pytest.raises(embeddings.EmbeddingError):
        embeddings.load_cache(path)


def fake_urlopen(body: bytes):
    class Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    return lambda request, timeout: Response(body)


@pytest.mark.parametrize(
    "body",
    [b"not json", json.dumps({"error": "model not found"}).encode(), json.dumps({"embeddings": [[1.0]]}).encode()],
)
def test_bad_ollama_response_raises_embedding_error(monkeypatch, body) -> None:
    monkeypatch.setattr(embeddings.urllib.request, "urlopen", fake_urlopen(body))
    with pytest.raises(embeddings.EmbeddingError):
        REAL_REQUEST(["one", "two"])


def test_committed_cache_covers_eval_set_offline(monkeypatch) -> None:
    """The shipped semantic config must run the whole eval set from the committed cache, without Ollama."""
    from src.eval_runner import run_eval

    monkeypatch.setattr(config, "RETRIEVAL_MODE", "semantic")
    run = run_eval()
    assert len(run["results"]) == 12
