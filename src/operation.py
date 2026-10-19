"""Cooperative cancellation and truthful progress for local background work."""
from contextlib import contextmanager
from contextvars import ContextVar
import time

_CURRENT = ContextVar('rag_operation', default=None)
_USAGE = ContextVar('rag_usage', default=None)

def record(kind, cached=False, metadata=None, seconds=0):
    usage=_USAGE.get()
    if usage is None:return
    counts = usage['cache_hits' if cached else 'requests']
    counts[kind] = counts.get(kind, 0) + 1
    if not cached:
        usage['model_seconds']+=seconds
        if kind in ('llm', 'jev'):
            metadata=metadata or {}
            unknown=False
            for field,key in (('prompt_eval_count','prompt_tokens'),('eval_count','output_tokens')):
                value=metadata.get(field)
                if isinstance(value,int) and not isinstance(value,bool) and value>=0:
                    usage[key]=(usage[key] or 0)+value
                else:unknown=True
            if unknown:usage['unknown_token_calls']+=1

@contextmanager
def measure():
    usage=dict(requests={'embeddings':0,'llm':0},cache_hits={'embeddings':0,'llm':0},prompt_tokens=None,output_tokens=None,unknown_token_calls=0,model_seconds=0,phases=[])
    token=_USAGE.set(usage)
    try:yield usage
    finally:
        if usage.get('_phase'):
            usage['phases'].append({'stage':usage.pop('_phase'),'seconds':round(time.perf_counter()-usage.pop('_phase_started'),6)})
        if usage['unknown_token_calls']:
            usage['prompt_tokens']=usage['output_tokens']=None
        _USAGE.reset(token)


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
    usage=_USAGE.get()
    if usage is not None:
        now=time.perf_counter()
        if usage.get('_phase'):
            usage['phases'].append({'stage':usage['_phase'],'seconds':round(now-usage['_phase_started'],6)})
        usage['_phase'],usage['_phase_started']=stage,now


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
