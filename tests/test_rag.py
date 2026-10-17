from src.chunking import build_chunks
from src.corpus import load_corpus
from src.rag import REFUSAL_MESSAGE, build_grounded_answer


def test_supported_question_returns_citations() -> None:
    result = build_grounded_answer("How often do passwords need to be changed?", build_chunks(load_corpus()))
    assert result.refused is False
    assert result.citations


def test_question_without_matching_words_is_refused() -> None:
    result = build_grounded_answer("Zebra xylophone quantum?", build_chunks(load_corpus()))
    assert result.refused is True
    assert result.citations == []
    assert result.answer == REFUSAL_MESSAGE
