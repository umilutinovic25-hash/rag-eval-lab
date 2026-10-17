from src import config
from src.chunking import Chunk, build_chunks
from src.corpus import load_corpus
from src.rag import REFUSAL_MESSAGE, build_grounded_answer, select_citations
from src.retrieval import RetrievalResult


def test_supported_question_returns_citations() -> None:
    result = build_grounded_answer("How often do passwords need to be changed?", build_chunks(load_corpus()))
    assert result.refused is False
    assert result.citations


def test_question_without_matching_words_is_refused() -> None:
    result = build_grounded_answer("Zebra xylophone quantum?", build_chunks(load_corpus()))
    assert result.refused is True
    assert result.citations == []
    assert result.answer == REFUSAL_MESSAGE


def result(chunk_id: str, score: float) -> RetrievalResult:
    return RetrievalResult(Chunk(chunk_id, chunk_id, "T", "2026", "current", "text"), score)


def test_citation_min_score_drops_weak_results_but_keeps_top(monkeypatch) -> None:
    monkeypatch.setattr(config, "CITATION_MIN_SCORE", 0.5)
    cited = select_citations([result("a", 0.4), result("b", 0.45), result("c", 0.3)])
    assert [item.chunk.chunk_id for item in cited] == ["a"]
    cited = select_citations([result("a", 0.9), result("b", 0.6), result("c", 0.2)])
    assert [item.chunk.chunk_id for item in cited] == ["a", "b"]


def test_citation_min_score_none_cites_everything(monkeypatch) -> None:
    monkeypatch.setattr(config, "CITATION_MIN_SCORE", None)
    assert len(select_citations([result("a", 0.9), result("b", 0.1)])) == 2


def test_citation_threshold_follows_retrieval_mode(monkeypatch) -> None:
    monkeypatch.setattr(config, "CITATION_MIN_SCORE", None)
    monkeypatch.setattr(config, "SEMANTIC_CITATION_MIN_SCORE", 0.5)
    results = [result("a", 0.9), result("b", 0.1)]
    assert len(select_citations(results)) == 2
    monkeypatch.setattr(config, "RETRIEVAL_MODE", "semantic")
    assert [item.chunk.chunk_id for item in select_citations(results)] == ["a"]
