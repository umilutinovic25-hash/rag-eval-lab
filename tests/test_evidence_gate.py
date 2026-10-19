"""Mechanics for the optional semantic gate; examples are synthetic, not eval items."""

from src import config, llm, rag
from src.chunking import build_chunks
from src.corpus import Document
from src.retrieval import RetrievalResult


def test_baseline_disables_new_behavior():
    before = config.snapshot()
    try:
        config.apply_profile('baseline')
        assert not any((config.VERSION_CONTEXT, config.IMPLICIT_BINARY, config.EVIDENCE_RELEVANCE))
    finally:
        for key, value in before.items():
            setattr(config, key, value)


def test_relevance_json_envelope_and_strict_verdict(monkeypatch):
    prompts = []
    monkeypatch.setattr(llm, 'generate', lambda model, prompt, tokens: prompts.append(prompt) or 'supported')
    assert llm.evidence_supports('Which shelf?', [{'text': 'Shelf B.'}])
    assert '"question": "Which shelf?"' in prompts[0]
    monkeypatch.setattr(llm, 'generate', lambda *a: 'supported but I guessed')
    assert not llm.evidence_supports('Which shelf?', [{'text': 'Shelf B.'}])
    monkeypatch.setattr(llm, 'generate', lambda *a: llm.GenerationText('supported', {'done_reason': 'length'}))
    assert not llm.evidence_supports('Which shelf?', [{'text': 'Shelf B.'}])


def test_high_score_still_requires_subject_evidence(monkeypatch):
    chunks = build_chunks([Document('s', 'Shelf policy', 'Storage', '2026', 'current', 'Use shelf B.')])
    monkeypatch.setattr(config, 'EVIDENCE_RELEVANCE', True)
    monkeypatch.setattr(config, 'ANSWER_MODE', 'llm')
    monkeypatch.setattr(config, 'RETRIEVAL_MODE', 'semantic')
    monkeypatch.setattr(config, 'RERANK', 'llm-gray-zone')
    monkeypatch.setattr(rag, 'retrieve_top_k', lambda *a, **k: [RetrievalResult(chunks[0], .95)])
    monkeypatch.setattr(llm, 'evidence_supports', lambda *a: False)
    answer = rag.build_grounded_answer('Which shelf has a lock?', chunks)
    assert answer.refused
    assert answer.trace[-1]['reason'] == 'evidence_missing_subject'


def test_version_query_below_floor_receives_metadata(monkeypatch):
    monkeypatch.setattr(config, 'VERSION_CONTEXT', True)
    chunks = build_chunks([Document('s', 'Shelf policy', 'Storage', '2026', 'current', 'Use shelf B.')])
    monkeypatch.setattr(config, 'RETRIEVAL_MODE', 'semantic')
    monkeypatch.setattr(config, 'RERANK', 'llm-gray-zone')
    monkeypatch.setattr(rag, 'retrieve_top_k', lambda *a, **k: [RetrievalResult(chunks[0], .42)])
    contexts = []
    monkeypatch.setattr(rag, 'passage_answers', lambda q, p: contexts.append(p) or True)
    answer = rag.build_grounded_answer('Which shelf is current?', chunks)
    assert not answer.refused
    assert 'status: current' in contexts[0]
    assert 'status: current' not in answer.answer


def test_implicit_second_chance_only_after_rejection(monkeypatch):
    monkeypatch.setattr(config, 'IMPLICIT_BINARY', True)
    monkeypatch.setattr(llm, 'base_passage_answers', lambda *a: False)
    prompts = []
    monkeypatch.setattr(llm, 'generate', lambda m, p, n: prompts.append(p) or 'no')
    assert llm.passage_answers('May I take nine?', 'The maximum is eight.')
    assert 'numerical limits' in prompts[0]
    prompts.clear()
    monkeypatch.setattr(llm, 'base_passage_answers', lambda *a: True)
    assert llm.passage_answers('May I take nine?', 'The maximum is eight.')
    assert not prompts
