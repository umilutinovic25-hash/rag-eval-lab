import pytest

from src import config, embeddings, llm


@pytest.fixture(autouse=True)
def offline_lexical_defaults(monkeypatch):
    """Tests check mechanics: lexical mode, no rerank, extractive answers by default, and never call Ollama."""
    monkeypatch.setattr(config, "RETRIEVAL_MODE", "lexical")
    monkeypatch.setattr(config, "RERANK", None)
    monkeypatch.setattr(config, "ANSWER_MODE", "extractive")
    monkeypatch.setattr(config, "ANSWER_QUOTES", False)
    monkeypatch.setattr(config, "CONTEXT_NEIGHBORS", 0)
    monkeypatch.setattr(config, "EVIDENCE_RULES_ENABLED", False)

    def no_network(texts):
        raise AssertionError(f"Test tried to call Ollama for {len(texts)} text(s)")

    monkeypatch.setattr(embeddings, "request_embeddings", no_network)

    def no_llm(model, prompt, max_tokens):
        raise AssertionError(f"Test tried to call Ollama model {model}")

    monkeypatch.setattr(llm, "request_generation", no_llm)
