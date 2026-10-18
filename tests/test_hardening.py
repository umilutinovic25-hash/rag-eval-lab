import pytest

from src import config, llm, rag
from src.chunking import Chunk
from src.retrieval import RetrievalResult


@pytest.mark.parametrize(
    'span,passage,accepted',
    [
        ('Budget is 900 EUR per employee.', 'Budget is 800 EUR per employee.', False),
        ('Share passwords with colleagues from IT.', 'Never share passwords, also not with colleagues from IT.', False),
        ('share passwords', 'Never share passwords.', False),
        ('budget carry over', 'Unused budget does not carry over.', False),
        ('Never share passwords', 'Never share passwords, also not with colleagues from IT.', True),
        ('800 EUR', 'Budget is 800 EUR per employee.', True),
        ('  "PARKING is limited"  ', 'Parking is limited: spaces are shared.', True),
        ('not carry over', 'Unused budget does not carry over.', True),
    ],
)
def test_span_preserves_words_order_numbers_and_negation(span, passage, accepted):
    assert llm.span_is_in_passage(span, passage) is accepted


@pytest.mark.parametrize('text', [
    '', '   ', 'Use 900 EUR [hb-08-chunk-0].',
    'Budget [hb-99-chunk-0].', 'Budget [hb-08-chunk-0',
    'Budget without any reference.',
    'Budget [hb-08-chunk-0].\nSource [hb-08-chunk-0]: "Invented policy"',
])
def test_invalid_generation_falls_back_to_real_cited_text(monkeypatch, text):
    c = Chunk('hb-08-chunk-0', 'hb-08', 'Budget', '2026', 'current', 'Training budget is 800 EUR.')
    monkeypatch.setattr(config, 'ANSWER_MODE', 'llm')
    monkeypatch.setattr(rag, 'retrieve_top_k', lambda *args, **kwargs: [RetrievalResult(c, 0.9)])
    monkeypatch.setattr(rag, 'write_answer', lambda *args: text)
    result = rag.build_grounded_answer('Budget?', [c])
    assert result.answer == 'Grounded response based on retrieved context:\n[hb-08-chunk-0] Training budget is 800 EUR.'
    assert result.generation_fallback_reason
    assert result.citations == [c.chunk_id] and not result.refused


def test_generation_failure_uses_sources_instead_of_crashing(monkeypatch):
    c = Chunk('a', 'd', 'T', '2026', 'current', 'Training budget is 800 EUR.')
    monkeypatch.setattr(config, 'ANSWER_MODE', 'llm')
    monkeypatch.setattr(rag, 'retrieve_top_k', lambda *args, **kwargs: [RetrievalResult(c, 0.9)])
    def fail(*args):
        raise llm.LLMError('Unavailable')
    monkeypatch.setattr(rag, 'write_answer', fail)
    result = rag.build_grounded_answer('Budget?', [c])
    assert c.text in result.answer and result.generation_fallback_reason == 'generation_error'
