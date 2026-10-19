"""Two independent empty-cache experiments of the accepted defaults; no gold-dependent tuning."""
import hashlib
import importlib.util
import json
import time
from pathlib import Path
from src import config, operation
from src.candidate_runner import run_set
from src.chunking import build_chunks
from src.corpus import load_corpus
from src.scratch import NAMES, use_scratch_caches

spec = importlib.util.spec_from_file_location('prime21', 'evidence/upgrade/prime-21.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
chunks = build_chunks(load_corpus())
names = ('test7', 'near3', 'implicit3', 'inject3')
for repeat in (1, 2):
    folder = Path(f'results/scratch-21-accepted-cold-{repeat}')
    folder.mkdir(parents=True, exist_ok=True)
    for name in NAMES:
        (folder / name).write_text('{}\n')
    initial = {name: {'entries': len(json.loads((folder / name).read_text())),
                      'sha256': hashlib.sha256((folder / name).read_bytes()).hexdigest()} for name in NAMES}
    use_scratch_caches(folder)
    report = {'repeat': repeat, 'config': config.snapshot(), 'initial_caches': initial,
              'set_sha256': {name: hashlib.sha256(Path(f'eval/{name}_set.json').read_bytes()).hexdigest()
                             for name in names}, 'sets': {}}
    started = time.perf_counter()
    with operation.measure() as usage:
        module.prime(names, chunks)
        for name in names:
            report['sets'][name] = run_set(name, chunks)
            Path(f'evidence/upgrade/cold-21-{repeat}.json').write_text(json.dumps(report, indent=2))
            print(repeat, name, report['sets'][name]['summary']['passed'], flush=True)
    report['seconds_including_priming'] = round(time.perf_counter() - started, 2)
    report['usage'] = {key: value for key, value in usage.items() if key != 'phases'}
    Path(f'evidence/upgrade/cold-21-{repeat}.json').write_text(json.dumps(report, indent=2))
