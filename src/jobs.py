"""Bounded, in-memory local jobs. One worker protects the globally configured RAG."""
from dataclasses import dataclass, field
import queue
import threading
import time
import uuid

from . import operation

TERMINAL = {'completed', 'cancelled', 'failed'}


class JobCapacityError(RuntimeError):
    pass


@dataclass
class Job:
    id: str
    body: dict
    created: float = field(default_factory=time.monotonic)
    status: str = 'queued'
    progress: dict = field(default_factory=lambda: {'stage': 'queued', 'message': 'Čeka na slobodan lokalni model.'})
    result: dict | None = None
    error: str | None = None
    finished: float | None = None
    cancel: threading.Event = field(default_factory=threading.Event)
    phases: list = field(default_factory=list)


class JobManager:
    def __init__(self, handler, capacity=16, retained=64, ttl=900, deadline=300):
        self.handler, self.capacity, self.retained, self.ttl, self.deadline = handler, capacity, retained, ttl, deadline
        self.jobs = {}
        self.lock = threading.RLock()
        self.queue = queue.Queue(maxsize=capacity+1)
        self.closed = threading.Event()
        self.worker = threading.Thread(target=self._work, daemon=True, name='izvor-jobs')
        self.worker.start()

    def _purge(self):
        now = time.monotonic()
        finished = sorted((j for j in self.jobs.values() if j.finished is not None), key=lambda j: j.finished)
        for index, job in enumerate(finished):
            if now - job.finished > self.ttl or index < len(finished) - self.retained:
                del self.jobs[job.id]

    def submit(self, body):
        with self.lock:
            self._purge()
            if self.closed.is_set() or sum(j.status not in TERMINAL for j in self.jobs.values()) >= self.capacity:
                raise JobCapacityError('Red je pun. Sačekajte završetak ili otkažite prethodni zahtev.')
            job = Job(uuid.uuid4().hex, dict(body))
            self.jobs[job.id] = job
            try:
                self.queue.put_nowait(job)
            except queue.Full:
                del self.jobs[job.id]
                raise JobCapacityError('Red je pun; prethodni model još završava otkazani zahtev.')
            return self._snapshot(job)

    def _snapshot(self, job):
        return dict(id=job.id, status=job.status, progress=dict(job.progress), result=job.result, error=job.error,
                    seconds=round((job.finished or time.monotonic()) - job.created, 3), phases=list(job.phases))

    def get(self, job_id):
        with self.lock:
            self._purge()
            job = self.jobs.get(job_id)
            return self._snapshot(job) if job else None

    def cancel(self, job_id):
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                return None
            if job.status not in TERMINAL:
                job.cancel.set()
                if job.status == 'queued':
                    job.status, job.finished = 'cancelled', time.monotonic()
                else:
                    job.status = 'cancelling'
                job.progress = {'stage': job.status, 'message': 'Otkazivanje; već započeti poziv modelu može još trajati.'}
            return self._snapshot(job)

    def close(self):
        self.closed.set()
        with self.lock:
            for job in list(self.jobs.values()):
                self.cancel(job.id)
        try:
            self.queue.put_nowait(None)
        except queue.Full:
            pass
        self.worker.join(timeout=1)

    def _work(self):
        while not self.closed.is_set():
            job = self.queue.get()
            if job is None:
                return
            with self.lock:
                if job.cancel.is_set():
                    continue
                job.status = 'running'
            def report(stage, message):
                with self.lock:
                    job.progress = {'stage': stage, 'message': message}
                    job.phases.append({'stage': stage, 'seconds': round(time.monotonic()-job.created, 3)})
                    job.phases[:] = job.phases[-100:]
            try:
                with operation.scope(job.cancel, report, job.created + self.deadline):
                    result = self.handler(**job.body)
                    operation.check()
                with self.lock:
                    # Cancellation can arrive after the last checkpoint, before publication.
                    if job.cancel.is_set():
                        raise operation.CancelledError()
                    elapsed = round(time.monotonic() - job.created, 3)
                    job.result = {**result, 'trace': [*result.get('trace', []),
                                  {'stage': 'timing', 'queue_and_work_seconds': elapsed,
                                   'phases': list(job.phases)}]}
                    job.status = 'completed'
            except operation.CancelledError:
                with self.lock:
                    job.status, job.result = 'cancelled', None
            except Exception as error:
                with self.lock:
                    job.status = 'failed'
                    job.error = str(error) if isinstance(error, (ValueError, TimeoutError)) else 'Lokalni model nije dostupan. Pokušajte ponovo ili izaberite režim Bez modela.'
            finally:
                with self.lock:
                    job.finished = time.monotonic()
                    job.progress = {'stage': job.status, 'message': {'completed': 'Odgovor je spreman.', 'cancelled': 'Obrada je otkazana.', 'failed': 'Obrada nije završena.'}.get(job.status, job.status)}
