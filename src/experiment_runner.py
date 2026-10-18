"""Run unchanged eval metrics with an explicit cache mode and reproducibility manifest."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import time
from unittest.mock import patch
import urllib.request

from . import config, embeddings, llm
from .corpus import load_corpus
from .eval_runner import EVAL_SET_PATH, run_eval
from .holdout_runner import HOLDOUT_SET_PATH, TEST_SET_PATH, TEST2_SET_PATH, run_holdout

ROOT = Path(__file__).resolve().parents[1]
SETS = {'eval': EVAL_SET_PATH, 'holdout': HOLDOUT_SET_PATH, 'test1': TEST_SET_PATH, 'test2': TEST2_SET_PATH}


def digest(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def git_revision() -> str:
    result = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else 'unknown'


def model_identity() -> dict:
    """Observed local identity is not provenance of already cached historical output."""
    try:
        with urllib.request.urlopen('http://localhost:11434/api/tags', timeout=5) as response:
            models = json.load(response)['models']
        with urllib.request.urlopen('http://localhost:11434/api/version', timeout=5) as response:
            version = json.load(response)['version']
        return {'status': 'observed', 'ollama_version': version,
                'models': {item['name']: item.get('digest') for item in models}}
    except (OSError, ValueError, KeyError, TypeError) as error:
        return {'status': 'unavailable', 'reason': str(error)}


def manifest(mode: str, inspect_models: bool = False) -> dict:
    corpus = json.dumps([asdict(doc) for doc in load_corpus()], sort_keys=True).encode()
    status = subprocess.run(['git', 'status', '--porcelain'], cwd=ROOT, capture_output=True, text=True)
    return {
        'created_at': datetime.now(timezone.utc).isoformat(), 'mode': mode,
        'git_revision': git_revision(),
        'git_dirty': bool(status.stdout.strip()) if status.returncode == 0 else None,
        'source_identity_note': 'Source hashes identify the files actually run; git_revision alone is insufficient when dirty.',
        'config': config.snapshot(),
        'source_sha256': {str(p.relative_to(ROOT)): digest(p) for p in sorted((ROOT / 'src').glob('*.py'))},
        'corpus_sha256': hashlib.sha256(corpus).hexdigest(),
        'question_set_sha256': {name: digest(path) for name, path in SETS.items()},
        'cache_sha256': {'embeddings': digest(embeddings.CACHE_PATH), 'llm': digest(llm.CACHE_PATH)},
        'generation_options': {'temperature': 0, 'seed': 7},
        'judge_max_tokens': {'span': 40, 'yesno': 3}, 'answer_max_tokens': 80,
        'historical_cache_model_digests': 'unknown: not recorded when historical caches were made',
        'observed_local_models': model_identity() if inspect_models else {'status': 'not_checked'},
    }


def execute(mode: str = 'replay', inspect_models: bool = False) -> dict:
    if mode not in ('replay', 'cold'):
        raise ValueError('mode must be replay or cold')
    info = manifest(mode, inspect_models or mode == 'cold')
    if mode == 'cold' and info['observed_local_models']['status'] != 'observed':
        raise llm.LLMError('Cold run requires a running local Ollama; no models are downloaded automatically.')
    calls = {'embeddings': 0, 'llm': 0}
    embed_request, llm_request = embeddings.request_embeddings, llm.request_generation

    def counted(kind, original):
        def call(*args, **kwargs):
            calls[kind] += 1
            if mode == 'replay':
                raise AssertionError(f'Replay attempted an uncached {kind} request')
            return original(*args, **kwargs)
        return call

    runs = {}
    with tempfile.TemporaryDirectory(prefix='rag-cold-') as temporary:
        embed_path = Path(temporary) / 'embeddings.json' if mode == 'cold' else embeddings.CACHE_PATH
        llm_path = Path(temporary) / 'llm.json' if mode == 'cold' else llm.CACHE_PATH
        with patch.object(embeddings, 'CACHE_PATH', embed_path), patch.object(llm, 'CACHE_PATH', llm_path), \
                patch.object(embeddings, 'request_embeddings', counted('embeddings', embed_request)), \
                patch.object(llm, 'request_generation', counted('llm', llm_request)):
            for name, path in SETS.items():
                before = dict(calls)
                started = time.perf_counter()
                run = run_eval() if name == 'eval' else run_holdout(path)
                runs[name] = {'run': run, 'seconds': time.perf_counter() - started,
                              'requests': {key: calls[key] - before[key] for key in calls}}
            info['used_cache_sha256'] = {'embeddings': digest(embed_path), 'llm': digest(llm_path)}
    info['request_totals'] = calls
    info['interpretation'] = ('Cached replay only; no fresh model generation.' if mode == 'replay'
                              else 'Fresh local model calls; isolated caches shared across the four sets.')
    return {'manifest': info, 'runs': runs}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['replay', 'cold'], default='replay')
    parser.add_argument('--inspect-models', action='store_true', help='Read identity from running local Ollama')
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    report = execute(args.mode, args.inspect_models)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    for name, entry in report['runs'].items():
        print(name, entry['run']['summary'], entry['requests'])
    print(report['manifest']['interpretation'])


if __name__ == '__main__':
    main()
