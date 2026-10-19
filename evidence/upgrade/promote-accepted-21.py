"""Historical broad-promotion experiment; final production policy uses curate-browser-cache-21.py.

Run the accepted defaults and promote only cache keys actually used by supported profiles.

Run only after selecting an unchanged, pre-registered candidate. Existing cache entries stay intact.
"""
import hashlib
import json
import sys
from pathlib import Path
from src import config, embeddings, llm
from src.candidate_runner import main
from src.scratch import NAMES

ROOT = Path.cwd()
used = {'embedding_cache.json': set(), 'llm_cache.json': set()}
original_embedding_key, original_llm_key = embeddings.cache_key, llm.cache_key

def embedding_key(*args, **kwargs):
    key = original_embedding_key(*args, **kwargs)
    used['embedding_cache.json'].add(key)
    return key

def llm_key(*args, **kwargs):
    key = original_llm_key(*args, **kwargs)
    used['llm_cache.json'].add(key)
    return key

embeddings.cache_key, llm.cache_key = embedding_key, llm_key
main()  # Uses the exact candidate_runner CLI, including the supplied scratch path.
# Browser comparison needs baseline and current with the real document filter, too.
from src import web
from src.library import Library
from src.store import Store
web.RUNTIME_DIR = llm.CACHE_PATH.parent
library = Library(Store(web.RUNTIME_DIR / 'browser-check.sqlite'))
browser = {}
for profile in ('baseline', 'current'):
    result = web.chat_payload('Is the training budget per team or per person?', profile,
                              filters={'doc_ids': ['hb-08']}, library=library)
    browser[profile] = result
Path('evidence/upgrade/browser-cache-21.json').write_text(json.dumps(browser, indent=2, ensure_ascii=False))
manifest = {'accepted_config': config.snapshot(), 'used_keys': {n: sorted(keys) for n, keys in used.items()}, 'promotions': {}}
for name in NAMES:
    target = ROOT / 'data' / name
    scratch = llm.CACHE_PATH.parent / name
    current, values = json.loads(target.read_text()), json.loads(scratch.read_text())
    keys = used['llm_cache.json' if name.endswith('-metadata.json') else name]
    added = {key: values[key] for key in keys - current.keys() if key in values}
    before = hashlib.sha256(target.read_bytes()).hexdigest()
    if added:
        current.update(added)
        embeddings.save_cache(current, target)
    manifest['promotions'][name] = {'added': sorted(added), 'before_sha256': before,
                                  'after_sha256': hashlib.sha256(target.read_bytes()).hexdigest()}
Path('evidence/upgrade/accepted-cache-21.json').write_text(json.dumps(manifest, indent=2))
