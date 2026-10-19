"""External adapter contracts and routing, with synthetic evidence and a fake transport."""
import copy
import json
import threading
import time
from urllib.error import HTTPError, URLError

import pytest

from src import config, jev, operation, rag
from src.chunking import Chunk
from src.retrieval import RetrievalResult

TRANSPORT = jev.request_decisions
CHUNK = Chunk('synthetic-0', 'synthetic', 'Storage', '2026', 'current', 'Use shelf B. No crates are allowed.')


def response(label='supported', p=.9, count=1):
    probabilities = dict.fromkeys(jev.LABELS, (1-p)/2)
    probabilities[label] = p
    return {'model': config.JEV_MODEL, 'answers': {
        f'p{i}': {'type': 'choice', 'choice': label, 'probabilities': probabilities.copy(),
                  'confidence': (p-1/3)/(1-1/3)} for i in range(count)},
        'usage': {'input_tokens': 123, 'output_tokens': 15}}


@pytest.fixture
def adapter(monkeypatch, tmp_path):
    monkeypatch.setattr(jev, 'CACHE_PATH', tmp_path/'jev_cache.json')
    monkeypatch.setattr(jev, 'KEY_FILE', tmp_path/'.env.jev')
    monkeypatch.delenv('TYPESAFE_API_KEY', raising=False)
    return tmp_path


def test_private_key_environment_priority_and_not_executed(adapter, monkeypatch):
    jev.KEY_FILE.write_text('TYPESAFE_API_KEY=private-fixture\nIGNORED=$(touch not-executed)\n')
    assert jev.api_key() == 'private-fixture'
    assert not (adapter/'not-executed').exists()
    monkeypatch.setenv('TYPESAFE_API_KEY', 'environment-fixture')
    assert jev.api_key() == 'environment-fixture'


def test_missing_credentials_are_sanitized(adapter):
    with pytest.raises(jev.JevError, match='missing_key'):
        TRANSPORT({})


def test_batch_mapping_cache_and_usage(adapter, monkeypatch):
    calls = []
    def fake(payload):
        calls.append(payload)
        body = response(count=2)
        body['debug'] = 'must-not-persist'
        return body
    monkeypatch.setattr(jev, 'request_decisions', fake)
    with operation.measure() as usage:
        first = jev.classify('Which shelf?', [CHUNK, CHUNK])
        second = jev.classify('Which shelf?', [CHUNK, CHUNK])
    assert len(calls) == 1 and all(d.accepted for d in first)
    assert not first[0].cached and second[0].cached
    assert calls[0]['state']['passages'][0]['status'] == 'current'
    assert 'state.passages[1]' in calls[0]['questions']['p1']['instructions']
    assert 'expected_fact' not in json.dumps(calls)
    assert 'must-not-persist' not in jev.CACHE_PATH.read_text()
    assert usage['requests']['jev'] == usage['cache_hits']['jev'] == 1
    assert usage['prompt_tokens'] == 123 and usage['output_tokens'] == 15


@pytest.mark.parametrize('label,p,accepted', [('contradicted',.9,True),('supported',.79,False),('insufficient',.99,False)])
def test_negative_answer_is_answerable_but_uncertain_is_not(adapter, monkeypatch, label, p, accepted):
    monkeypatch.setattr(jev, 'request_decisions', lambda payload: response(label,p))
    assert jev.classify('May I use crates?', [CHUNK])[0].accepted is accepted


@pytest.mark.parametrize('damage', [
    lambda b: b.update(model='jev-latest'),
    lambda b: b['answers'].update(p1=copy.deepcopy(b['answers']['p0'])),
    lambda b: b['answers']['p0'].update(choice='other'),
    lambda b: b['answers']['p0'].update(type='noul'),
    lambda b: b['answers']['p0']['probabilities'].update(supported=float('nan')),
    lambda b: b['answers']['p0']['probabilities'].update(supported=True),
    lambda b: b['answers']['p0']['probabilities'].update(insufficient=.8),
    lambda b: b['answers']['p0'].update(confidence=.01),
    lambda b: b.update(usage={'input_tokens':-1,'output_tokens':2}),
])
def test_bad_or_wrong_version_output_is_not_cached(adapter, monkeypatch, damage):
    body = response()
    damage(body)
    monkeypatch.setattr(jev, 'request_decisions', lambda payload: body)
    with pytest.raises(jev.JevError):
        jev.classify('Which shelf?', [CHUNK])
    assert not jev.CACHE_PATH.exists()


def test_corrupt_cached_response_is_not_trusted(adapter, monkeypatch):
    monkeypatch.setattr(jev, 'request_decisions', lambda payload: response())
    jev.classify('Which shelf?', [CHUNK])
    cache = json.loads(jev.CACHE_PATH.read_text())
    next(iter(cache.values()))['answers']['p0']['probabilities']['supported'] = 0
    jev.CACHE_PATH.write_text(json.dumps(cache))
    with pytest.raises(jev.JevError, match='invalid_response'):
        jev.classify('Which shelf?', [CHUNK])


@pytest.mark.parametrize('error,code', [
    (HTTPError(jev.ENDPOINT,401,'sensitive-data',{},None),'authentication'),
    (HTTPError(jev.ENDPOINT,429,'sensitive-data',{},None),'rate_limit'),
    (HTTPError(jev.ENDPOINT,302,'sensitive-data',{},None),'unavailable'),
    (URLError('sensitive-data'),'unavailable'),
    (TimeoutError('sensitive-data'),'timeout'),
])
def test_transport_is_bounded_and_errors_do_not_leak(adapter, monkeypatch, error, code):
    monkeypatch.setenv('TYPESAFE_API_KEY','secret-fixture')
    calls=[]
    class FakeOpener:
        def open(self, request, timeout):
            calls.append((request, timeout))
            raise error
    monkeypatch.setattr(jev.urllib.request,'build_opener',lambda *a: FakeOpener())
    with pytest.raises(jev.JevError) as exc:
        TRANSPORT({'model':config.JEV_MODEL})
    assert exc.value.code == code and len(calls)==1
    assert 'secret-fixture' not in str(exc.value) and 'sensitive-data' not in str(exc.value)
    assert calls[0][0].get_header('Authorization') == 'Bearer secret-fixture'
    assert calls[0][1] == config.JEV_TIMEOUT_SECONDS


def test_cancellation_before_call_does_not_touch_transport(adapter, monkeypatch):
    cancel=threading.Event()
    with operation.scope(cancel,lambda *a:None,time.monotonic()+10):
        cancel.set()
        with pytest.raises(operation.CancelledError):
            jev.classify('Which shelf?', [CHUNK])
    assert not jev.CACHE_PATH.exists()


def test_offline_and_baseline_disable_external_calls(monkeypatch):
    for profile in ('offline','baseline'):
        monkeypatch.setattr(config,'JEV_ENABLED',True)
        config.apply_profile(profile)
        assert config.JEV_ENABLED is False


@pytest.mark.parametrize('score', [.2,.95])
def test_jev_checks_both_sides_of_local_gray_zone(adapter, monkeypatch, score):
    monkeypatch.setattr(config,'JEV_ENABLED',True)
    monkeypatch.setattr(config,'RETRIEVAL_MODE','semantic')
    monkeypatch.setattr(config,'RERANK','llm-gray-zone')
    monkeypatch.setattr(rag,'retrieve_top_k',lambda *a,**k:[RetrievalResult(CHUNK,score)])
    monkeypatch.setattr(jev,'request_decisions',lambda p:response('contradicted'))
    result=rag.build_grounded_answer('May I put crates there?', [CHUNK])
    assert not result.refused and result.citations == [CHUNK.chunk_id]
    assert any(step['stage']=='jev' and step['label']=='contradicted' for step in result.trace)


def test_high_similarity_does_not_override_insufficient_evidence(adapter, monkeypatch):
    monkeypatch.setattr(config,'JEV_ENABLED',True)
    monkeypatch.setattr(rag,'retrieve_top_k',lambda *a,**k:[RetrievalResult(CHUNK,.99)])
    monkeypatch.setattr(jev,'request_decisions',lambda p:response('insufficient'))
    result=rag.build_grounded_answer('Who cleans the shelf?', [CHUNK])
    assert result.refused and not result.citations
    assert result.trace[-1]['reason']=='jev_insufficient_evidence'


def test_provider_failure_does_not_fall_through_to_another_judge(adapter, monkeypatch):
    monkeypatch.setattr(config,'JEV_ENABLED',True)
    monkeypatch.setattr(rag,'retrieve_top_k',lambda *a,**k:[RetrievalResult(CHUNK,.99)])
    def fail(p):raise jev.JevError('rate_limit')
    monkeypatch.setattr(jev,'request_decisions',fail)
    result=rag.build_grounded_answer('Which shelf?', [CHUNK])
    assert result.refused and result.trace[-1]['reason']=='jev_unavailable'
    assert any(s.get('code')=='rate_limit' for s in result.trace)


def test_evidence_shortcut_does_not_bypass_jev(adapter, monkeypatch):
    from src import evidence
    monkeypatch.setattr(config,'JEV_ENABLED',True)
    monkeypatch.setattr(config,'EVIDENCE_RULES_ENABLED',True)
    monkeypatch.setattr(evidence,'select',lambda *a:('synthetic answer',[RetrievalResult(CHUNK,.9)],'synthetic_rule'))
    monkeypatch.setattr(jev,'request_decisions',lambda p:response('insufficient'))
    result=rag.build_grounded_answer('Which shelf?', [CHUNK])
    assert result.refused and result.trace[-1]['reason']=='jev_insufficient_evidence'
