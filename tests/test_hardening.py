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

from src import embeddings


@pytest.mark.parametrize('a,b', [([1, 0], [1]), ([float('nan')], [1]), ([float('inf')], [1]), (['x'], [1]), ([True], [1]), ([], [])])
def test_cosine_rejects_invalid_vectors(a, b):
    with pytest.raises(embeddings.EmbeddingError):
        embeddings.cosine(a, b)


def test_cache_rejects_valid_json_with_wrong_shape(tmp_path):
    p = tmp_path / 'cache.json'
    p.write_text('[]')
    with pytest.raises(embeddings.EmbeddingError):
        embeddings.load_cache(p)


def test_embed_rejects_bad_cached_vector(tmp_path, monkeypatch):
    p = tmp_path / 'cache.json'
    embeddings.save_cache({embeddings.cache_key('q'): ['x']}, p)
    monkeypatch.setattr(embeddings, 'CACHE_PATH', p)
    with pytest.raises(embeddings.EmbeddingError):
        embeddings.embed(['q'])


def test_llm_rejects_empty_or_nontext_cache(tmp_path, monkeypatch):
    p = tmp_path / 'llm.json'
    monkeypatch.setattr(llm, 'CACHE_PATH', p)
    for value in ['', '  ', [1, 2]]:
        embeddings.save_cache({llm.cache_key('m', 'p', 3): value}, p)
        with pytest.raises(llm.LLMError):
            llm.generate('m', 'p', 3)
