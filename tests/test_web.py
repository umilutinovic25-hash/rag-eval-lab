"""HTTP contracts, real cached RAG, and isolation of module-global profiles."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import json
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from src import config, rag, web


@contextmanager
def running_server(tmp_path):
    (tmp_path / 'index.html').write_text('<html>izvor.</html>')
    previous_runtime=web.RUNTIME_DIR
    server = web.make_server(0, tmp_path, state_dir=tmp_path/'state')
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_address[1]}'
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        web.RUNTIME_DIR=previous_runtime


def request(base, path, body=None, headers=None):
    headers = {'Content-Type': 'application/json', **(headers or {})}
    req = Request(base + path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
    try:
        response = urlopen(req, timeout=10)
    except HTTPError as error:
        response = error
    with response:
        return response.status, json.loads(response.read())


def test_cached_current_after_offline_and_restore():
    before = config.snapshot()
    offline = web.chat_payload('How many days per week can I work remotely?', 'offline')
    current = web.chat_payload('How many days per week can I work remotely?', 'current')
    assert not offline['refused']
    assert '3 days per week' in current['answer']
    assert current['profile'] == 'current'
    assert current['citations'][0]['version'] == '2026'
    assert current['citations'][0]['text']
    assert current['trace']
    assert config.snapshot() == before


def test_profiles_serialized_even_during_errors(monkeypatch):
    before = config.snapshot()
    observations = []

    def fake_build(question, chunks):
        initial = config.RETRIEVAL_MODE
        time.sleep(0.005)
        observations.append((question, initial, config.RETRIEVAL_MODE))
        if question == 'error':
            raise RuntimeError('test error')
        return rag.RagAnswer('ok', [], False, [], trace=[])

    monkeypatch.setattr(rag, 'build_grounded_answer', fake_build)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda mode: web.chat_payload(mode, mode), ['offline', 'current'] * 4))
    assert len(results) == 8
    assert all(first == last == ('lexical' if question == 'offline' else 'semantic') for question, first, last in observations)
    with pytest.raises(RuntimeError):
        web.chat_payload('error', 'current')
    assert config.snapshot() == before


@pytest.mark.parametrize('question', ['', ' ', None, 12, 'a' * 2001])
def test_reject_invalid_question(question):
    with pytest.raises(ValueError):
        web.chat_payload(question)


def test_http_chat_documents_and_missing_routes(tmp_path):
    with running_server(tmp_path) as base:
        status, docs = request(base, '/api/documents')
        assert status == 200
        assert len(docs['documents']) == 10
        assert len([d for d in docs['documents'] if d['status'] == 'superseded']) == 1
        status, answer = request(base, '/api/chat', {'question': 'How many days of annual leave do employees get?', 'profile': 'offline'})
        assert status == 200
        assert '22 days' in answer['answer']
        assert all(c['status'] == 'current' for c in answer['citations'])
        assert request(base, '/api/missing')[0] == 404
        assert request(base, '/api/missing', {})[0] == 404
        assert request(base, '/%2e%2e/secret')[0] == 404
        assert request(base, '/api/chat', {'question': 'ok', 'profile': 'wrong'})[0] == 400
        assert request(base, '/api/chat', [1, 2])[0] == 400


def test_status_counts_loaded_corpus_instead_of_fixed_totals(monkeypatch, tmp_path):
    documents = web.load_corpus()[:3]
    monkeypatch.setattr(web, 'load_corpus', lambda: documents)
    def offline(*args, **kwargs):
        raise OSError('test: Ollama offline')
    monkeypatch.setattr(web.urllib.request, 'urlopen', offline)
    with running_server(tmp_path) as base:
        status, data = request(base, '/api/status')
        assert status == 200
        assert data['documents'] == 3
        assert data['current_documents'] == 2
        assert data['ollama'] is False


def test_http_rejects_cross_origin_and_dns_rebinding(tmp_path):
    with running_server(tmp_path) as base:
        data = {'question': 'How many days of annual leave do employees get?', 'profile': 'offline'}
        assert request(base, '/api/chat', data, {'Origin': 'https://attacker.example'})[0] == 403
        assert request(base, '/api/documents', headers={'Host': 'attacker.example'})[0] == 403
        assert request(base, '/api/chat', data, {'Content-Type': 'text/plain'})[0] == 415
        assert request(base, '/api/chat', {'question': 'a' * 13000})[0] == 413


def test_http_returns_actionable_model_error(monkeypatch, tmp_path):
    def unavailable(*args):
        raise web.embeddings.EmbeddingError('model unavailable')
    monkeypatch.setattr(rag, 'build_grounded_answer', unavailable)
    with running_server(tmp_path) as base:
        status, data = request(base, '/api/chat', {'question': 'new question'})
        assert status == 503
        assert 'Bez modela' in data['error']


def test_http_replays_all_sets_without_network(tmp_path):
    with running_server(tmp_path) as base:
        status, saved = request(base, '/api/evaluations')
        assert status == 200
        assert saved['origin'] == 'saved'
        status, fresh = request(base, '/api/evaluations/run', {})
        assert status == 200
        assert fresh['origin'] == 'replayed'
        assert fresh['requests'] == {'embeddings': 0, 'llm': 0}
        for name in ('eval', 'holdout', 'test1', 'test2'):
            assert fresh['runs'][name]['summary']['total'] == saved['runs'][name]['summary']['total']
            assert fresh['runs'][name]['summary']['passed'] >= saved['runs'][name]['summary']['passed']
        assert fresh['question_set_sha256'] == saved['question_set_sha256']
        assert fresh['runs']['test2']['summary']['passed'] == 32


def test_static_headers_and_malformed_json(tmp_path):
    with running_server(tmp_path) as base:
        with urlopen(base) as response:
            assert response.status == 200
            assert response.headers['X-Content-Type-Options'] == 'nosniff'
            assert "frame-ancestors 'none'" in response.headers['Content-Security-Policy']
        req = Request(base + '/api/chat', data=b'{not-json', headers={'Content-Type': 'application/json'})
        with pytest.raises(HTTPError) as error:
            urlopen(req)
        assert error.value.code == 400
