"""Remove this experiment's broad promotion, retaining only actual browser-profile dependencies.

Only keys listed as newly added by the recorded promotion are eligible for removal.
Existing and unrelated entries are preserved. Experimental full caches remain in scratch.
"""
import hashlib
import json
from pathlib import Path
from src import config, embeddings, llm, web
from src.library import Library
from src.store import Store

record = json.loads(Path('evidence/upgrade/full-cache-promotion-attempt-21.json').read_text())
used = {'embedding_cache.json': set(), 'llm_cache.json': set()}
original_e, original_l = embeddings.cache_key, llm.cache_key

def ek(*a, **k):
    key = original_e(*a, **k)
    used['embedding_cache.json'].add(key)
    return key

def lk(*a, **k):
    key = original_l(*a, **k)
    used['llm_cache.json'].add(key)
    return key

def forbidden(*a, **k):
    raise AssertionError('Browser dependency capture must use recorded scratch results')

embeddings.cache_key, llm.cache_key = ek, lk
embeddings.request_embeddings = llm.request_generation = forbidden
web.RUNTIME_DIR = Path('results/scratch-21-ablate')
library = Library(Store(web.RUNTIME_DIR / 'browser-check.sqlite'))
for profile in ('baseline', 'current'):
    web.chat_payload('Is the training budget per team or per person?', profile,
                     filters={'doc_ids': ['hb-08']}, library=library)
result = {'accepted_config': config.snapshot(), 'policy': 'Only browser dependencies promoted; experiment keys stay in scratch.',
          'used_keys': {name: sorted(keys) for name, keys in used.items()}, 'promotions': {}}
for name, before in record['promotions'].items():
    path = Path('data') / name
    values = json.loads(path.read_text())
    wanted = used['llm_cache.json' if name.endswith('-metadata.json') else name]
    removed = set(before['added']) - wanted
    for key in removed:
        values.pop(key, None)
    embeddings.save_cache(values, path)
    result['promotions'][name] = {'added': sorted(set(before['added']) & wanted), 'pruned_experiment_entries': len(removed),
                                  'before_sha256': before['before_sha256'], 'after_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
Path('evidence/upgrade/accepted-cache-21.json').write_text(json.dumps(result, indent=2))
print({name: len(v['added']) for name, v in result['promotions'].items()})
