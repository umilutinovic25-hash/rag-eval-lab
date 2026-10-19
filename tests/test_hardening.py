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


def test_offline_profile_runs_new_question_without_models(monkeypatch):
    names = ['RETRIEVAL_MODE', 'RERANK', 'ANSWER_MODE', 'ANSWER_QUOTES']
    for name in names:
        monkeypatch.setattr(config, name, getattr(config, name))
    config.apply_profile('offline')
    assert config.RETRIEVAL_MODE == 'lexical' and config.RERANK is None
    c = Chunk('a', 'd', 'T', '2026', 'current', 'Parking is reserved through facilities app.')
    result = rag.build_grounded_answer('parking reserved facilities', [c])
    assert not result.refused and c.text in result.answer


def test_empty_question_does_not_retrieve_or_generate(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Empty questions must not call retrieval')
    monkeypatch.setattr(rag, 'retrieve_top_k', forbidden)
    assert rag.build_grounded_answer(' \n ', []).refused


def test_gray_zone_rejects_lexical_scale(monkeypatch):
    monkeypatch.setattr(config, 'RETRIEVAL_MODE', 'lexical')
    monkeypatch.setattr(config, 'RERANK', 'llm-gray-zone')
    with pytest.raises(ValueError, match='semantic'):
        rag.build_grounded_answer('a question', [])


def test_offline_cli_profile():
    import subprocess
    import sys
    result = subprocess.run([sys.executable, "-m", "src.cli", "--profile", "offline", "--question", "How many days of annual leave do employees get?"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "22 days" in result.stdout

from src import answer_quality


def test_answer_review_flags_contradiction_without_certifying_correctness():
    answer = 'Passwords do not need to be changed every 90 days [hb-05-chunk-0].'
    flags = answer_quality.review_flags(answer, ['Passwords must be changed every 90 days.'], 'every 90 days')
    assert 'negation_mismatch' in flags
    assert 'number_not_in_sources' in answer_quality.review_flags('Budget is 900 EUR.', ['Budget is 800 EUR.'], '800 EUR')


def test_quality_includes_refusals_in_denominator(tmp_path, monkeypatch):
    import json
    p = tmp_path / 'set.json'
    p.write_text(json.dumps([{'id':'Q1','question':'q','expected_behaviour':'answer','expected_fact':'22 days','expected_doc_ids':['hb-07']}]))
    monkeypatch.setattr(answer_quality, 'build_grounded_answer', lambda *args: rag.RagAnswer('No evidence', [], True, []))
    report = answer_quality.run(p)
    assert report['supported_total'] == 1
    assert report['false_refusals'] == 1 and report['answered_supported'] == 0
    assert len(report['rows']) == 1
    assert report['rows'][0]['semantic_correctness'] == 'not_assessed'


def test_test2_available_for_answer_quality():
    assert 'test2' in answer_quality.SETS


def test_manifest_hashes_corpus_code_and_all_sets():
    from src.experiment_runner import manifest
    report = manifest('replay')
    assert len(report['corpus_sha256']) == 64
    assert report['source_sha256']['src/rag.py']
    assert set(report['question_set_sha256']) == {'eval', 'holdout', 'test1', 'test2'}
    assert report['observed_local_models']['status'] == 'not_checked'
    assert report['historical_cache_model_digests'].startswith('unknown')


def test_replay_forbids_network_and_reports_zero_calls(monkeypatch):
    from src.experiment_runner import execute
    monkeypatch.setattr(config, 'RETRIEVAL_MODE', 'semantic')
    monkeypatch.setattr(config, 'RERANK', 'llm-gray-zone')
    monkeypatch.setattr(config, 'ANSWER_MODE', 'llm')
    monkeypatch.setattr(config, 'POLARITY_CHECK', False)  # the replay manifest predates the polarity check
    report = execute('replay')
    assert report['manifest']['request_totals'] == {'embeddings': 0, 'llm': 0}
    assert report['runs']['eval']['run']['summary']['passed'] == 12
