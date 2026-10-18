from dataclasses import replace
import threading
import time
import pytest
from src import localization, operation
from src.chunking import build_chunks
from src.corpus import load_corpus
from src.jobs import JobManager, JobCapacityError


def test_translation_rejects_a_changed_source():
    chunks=build_chunks(load_corpus())
    assert len(localization.localized_chunks(chunks))==len(chunks)
    chunks[0]=replace(chunks[0],text=chunks[0].text+' New condition.')
    with pytest.raises(ValueError,match='prevod ne odgovara'):localization.localized_chunks(chunks)


def test_cancelled_queued_jobs_cannot_grow_an_unbounded_queue():
    entered,release=threading.Event(),threading.Event()
    def handler(question):
        entered.set();release.wait(2);operation.check();return {'trace':[]}
    manager=JobManager(handler,capacity=2)
    try:
        first=manager.submit({'question':'active'})
        assert entered.wait(1)
        second=manager.submit({'question':'queued'})
        with pytest.raises(JobCapacityError):manager.submit({'question':'too many'})
        assert manager.cancel(second['id'])['status']=='cancelled'
        for i in range(10):
            try:
                queued=manager.submit({'question':str(i)})
            except JobCapacityError:break
            manager.cancel(queued['id'])
        else:pytest.fail('Cancelled work bypassed the queue bound')
        assert manager.get(first['id'])['status']=='running'
    finally:
        release.set();manager.close()


def test_deadline_fails_before_starting_the_handler():
    called=[]
    manager=JobManager(lambda question:called.append(question),deadline=0)
    try:
        job=manager.submit({'question':'expired'})
        deadline=time.monotonic()+1
        while time.monotonic()<deadline:
            status=manager.get(job['id'])
            if status['status']=='failed':break
            time.sleep(.01)
        assert status['status']=='failed'
        assert 'vreme obrade' in status['error']
        assert not called
    finally:manager.close()


def test_completed_jobs_expire():
    manager=JobManager(lambda question:{'trace':[]},ttl=0)
    try:
        job=manager.submit({'question':'short'})
        deadline=time.monotonic()+1
        while manager.get(job['id']) is not None and time.monotonic()<deadline:time.sleep(.01)
        assert manager.get(job['id']) is None
    finally:manager.close()


def test_cancel_while_waiting_for_legacy_pipeline_lock():
    from src import web
    manager=JobManager(lambda question:web.chat_payload(question,'offline'))
    web.PIPELINE_LOCK.acquire()
    try:
        job=manager.submit({'question':'waiting'})
        deadline=time.monotonic()+1
        while manager.get(job['id'])['status']=='queued' and time.monotonic()<deadline:time.sleep(.01)
        manager.cancel(job['id'])
        deadline=time.monotonic()+.5
        while manager.get(job['id'])['status']!='cancelled' and time.monotonic()<deadline:time.sleep(.01)
        assert manager.get(job['id'])['status']=='cancelled'
    finally:
        web.PIPELINE_LOCK.release();manager.close()
