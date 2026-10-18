"""Cooperative cancellation and truthful progress for local background work."""
from contextlib import contextmanager
from contextvars import ContextVar
import time

_CURRENT = ContextVar('rag_operation', default=None)


class CancelledError(RuntimeError):
    pass


def check():
    state = _CURRENT.get()
    if state:
        cancel, _, deadline = state
        if cancel.is_set():
            raise CancelledError('Obrada je otkazana.')
        if time.monotonic() >= deadline:
            raise TimeoutError('Isteklo je dozvoljeno vreme obrade. Pokušajte režim Bez modela.')


def progress(stage, message):
    check()
    state = _CURRENT.get()
    if state:
        state[1](stage, message)


def timeout(default):
    check()
    state = _CURRENT.get()
    return min(default, max(.1, state[2] - time.monotonic())) if state else default


@contextmanager
def scope(cancel, report, deadline):
    token = _CURRENT.set((cancel, report, deadline))
    try:
        check()
        yield
    finally:
        _CURRENT.reset(token)
