"""Opt-in digest namespaces; historical keys remain byte-identical outside bind()."""
from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import json
import urllib.request

_IDENTITY = ContextVar('model_identity', default=None)

def observe():
    with urllib.request.urlopen('http://127.0.0.1:11434/api/tags',timeout=3) as response:
        data=json.load(response)
    models={m['name']:m['digest'] for m in data['models'] if isinstance(m.get('digest'),str) and m['digest']}
    if not models:raise ValueError('Nema dostupnih identiteta modela.')
    return {'status':'live_observed','models':models}

def digest(model):
    state=_IDENTITY.get()
    if state is None:return None
    value=state['models'].get(model) or state['models'].get(model+':latest')
    if not value:raise ValueError('Digest nije poznat za model '+model)
    return value

def key(legacy,model,options):
    value=digest(model)
    return hashlib.sha256(json.dumps([legacy,value,options],sort_keys=True).encode()).hexdigest() if value else legacy

def require_live(model):
    state=_IDENTITY.get()
    if state and state['status']!='live_observed':
        raise ValueError('Offline identitet dozvoljava samo postojeći keš. Pokrenite Ollama za novi odgovor.')
    return digest(model)

def verify(model,before):
    if before:
        current=observe()['models']
        if (current.get(model) or current.get(model+':latest'))!=before:
            raise ValueError('Identitet modela se promenio tokom zahteva; rezultat nije sačuvan.')

@contextmanager
def bind(identity):
    token=_IDENTITY.set(identity)
    try:yield
    finally:_IDENTITY.reset(token)
