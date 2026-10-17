import pytest

from src import config, embeddings


@pytest.fixture(autouse=True)
def offline_lexical_defaults(monkeypatch):
    """Tests check mechanics: lexical mode by default and never call Ollama."""
    monkeypatch.setattr(config, "RETRIEVAL_MODE", "lexical")

    def no_network(texts):
        raise AssertionError(f"Test tried to call Ollama for {len(texts)} text(s)")

    monkeypatch.setattr(embeddings, "request_embeddings", no_network)
