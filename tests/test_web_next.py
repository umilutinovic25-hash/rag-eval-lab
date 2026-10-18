import threading
import time
import pytest
from src import web, rag
from test_web import running_server, request


def test_serbian_offline_answer_keeps_english_originals():
    result = web.chat_payload('Rad na daljinu: koliko dana nedeljno?', 'offline', language='sr')
    assert result['language'] == 'sr'
    assert '3 dana' in result['answer']
    assert '3 days' in result['citations'][0]['text']
    assert result['question'] == 'Rad na daljinu: koliko dana nedeljno?'
    assert result['translation_review_status'] == 'assistant_translation_pending_human_review'


def test_cyrillic_query_and_localized_refusal():
    result = web.chat_payload('Рад на даљину: колико дана недељно?', 'offline', language='auto')
    assert result['language'] == 'sr'
    assert '3 dana' in result['answer']
    assert result['question'].startswith('Рад')
    result = web.chat_payload('квантна гравитација', 'offline', language='sr')
    assert result['refused']
    assert 'Nemam dovoljno' in result['answer']


def test_jobs_return_promptly_cancel_and_do_not_block_documents(monkeypatch, tmp_path):
    entered, release = threading.Event(), threading.Event()
    def blocked(question, chunks):
        entered.set()
        release.wait(3)
        return rag.RagAnswer('ok', [], False, [])
    monkeypatch.setattr(rag, 'build_grounded_answer', blocked)
    with running_server(tmp_path) as base:
        try:
            status, job = request(base, '/api/jobs', {'question': 'pending', 'profile': 'offline'})
            assert status == 202
            assert entered.wait(1)
            assert request(base, '/api/documents')[0] == 200
            status, cancel = request(base, '/api/jobs/'+job['id']+'/cancel', {})
            assert status == 200
            assert cancel['status'] == 'cancelling'
        finally:
            release.set()
        deadline = time.monotonic()+2
        while time.monotonic()<deadline:
            status, final = request(base, '/api/jobs/'+job['id'])
            if final['status'] == 'cancelled': break
            time.sleep(.01)
        assert final['status'] == 'cancelled'
        assert final['result'] is None


def test_job_completed_result_and_unknown_id(tmp_path):
    with running_server(tmp_path) as base:
        status, job = request(base, '/api/jobs', {'question': 'How many days of annual leave do employees get?', 'profile': 'offline'})
        assert status == 202
        deadline = time.monotonic()+2
        while time.monotonic()<deadline:
            status, job = request(base, '/api/jobs/'+job['id'])
            if job['status'] in ('completed','failed'): break
            time.sleep(.01)
        assert job['status'] == 'completed'
        assert '22 days' in job['result']['answer']
        assert job['progress']['stage'] == 'completed'
        assert job['seconds'] >= 0
        assert request(base, '/api/jobs/not-found')[0] == 404


def test_completed_job_retains_measured_phases_in_answer_trace(tmp_path):
    with running_server(tmp_path) as base:
        _, job = request(base, '/api/jobs', {'question': 'How many days of annual leave do employees get?', 'profile': 'offline'})
        deadline = time.monotonic()+2
        while time.monotonic()<deadline:
            _, job = request(base, '/api/jobs/'+job['id'])
            if job['status'] in ('completed','failed'): break
            time.sleep(.01)
        assert job['status'] == 'completed'
        timings=[s for s in job['result']['trace'] if s['stage']=='timing']
        assert timings and timings[0]['phases']
        assert timings[0]['queue_and_work_seconds'] >= 0


def test_serbian_reference_expands_to_the_preceding_original_source():
    from src.chunking import Chunk
    from src.retrieval import RetrievalResult
    first=Chunk('a','doc','T','2026','current','Zahtev je u IT portalu, u odeljku Hardware.')
    second=Chunk('b','doc','T','2026','current','Slušalice se naručuju kroz isti taj formular.')
    expanded=rag.expand_context([RetrievalResult(second,.8)],[first,second],1,'references')
    assert [r.chunk.chunk_id for r in expanded]==['a','b']
