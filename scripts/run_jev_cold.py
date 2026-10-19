"""Repeat the frozen Jev set with empty caches; no alternate grading or prompt changes."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config, embeddings, operation
from src.candidate_runner import corpus_chunks, run_set
from src import candidate_runner
from src.chunking import build_chunks
from src.corpus import load_corpus
from src.retrieval import chunk_embedding_text, searchable_chunks
from src.scratch import NAMES, use_scratch_caches


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repeat', type=int, required=True, choices=(1, 2))
    args = parser.parse_args()
    folder = Path(f'results/scratch-jev-cold-{args.repeat}')
    folder.mkdir(parents=True, exist_ok=True)
    names = (*NAMES, 'jev_cache.json')
    if any((folder / n).exists() and json.loads((folder / n).read_text()) for n in names):
        raise SystemExit('Refusing to overwrite nonempty cold-run caches.')
    for name in names:
        (folder / name).write_text('{}\n')
    initial = {name: {'entries': 0, 'sha256': hashlib.sha256((folder / name).read_bytes()).hexdigest()} for name in names}
    use_scratch_caches(folder)
    config.JEV_ENABLED = True
    default = build_chunks(load_corpus())
    chunks = corpus_chunks('jev', default)
    questions = [item['question'] for item in json.loads(Path('eval/jev_set.json').read_text())]
    traces = {}
    original_build = candidate_runner.build_grounded_answer
    def traced(question, source):
        result = original_build(question, source)
        traces[question] = [s for s in result.trace if s['stage'] in ('jev', 'jev_error', 'decision', 'context')]
        return result
    candidate_runner.build_grounded_answer = traced
    started = time.perf_counter()
    with operation.measure() as usage:
        # Batch vectors only, with unchanged text/settings; this also computes unused guard-blocked queries.
        embeddings.embed(list(dict.fromkeys(questions + [chunk_embedding_text(c) for c in searchable_chunks(chunks)])))
        result = run_set('jev', default)
    report = {'repeat': args.repeat, 'candidate': 'jev', 'initial_caches': initial,
              'config': config.snapshot(), 'sets': {'jev': result}, 'usage': usage, 'traces': traces,
              'set_sha256': hashlib.sha256(Path('eval/jev_set.json').read_bytes()).hexdigest(),
              'elapsed_total_s': round(time.perf_counter() - started, 3),
              'execution_note': 'Embeddings batched before evaluation, including guard-blocked questions; no LLM priming and no grading changes.'}
    target = Path(f'evidence/upgrade/jev-cold-{args.repeat}.json')
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(f"repeat {args.repeat}: {result['summary']['passed']}/40; requests={usage['requests']}; total={report['elapsed_total_s']}s", flush=True)


if __name__ == '__main__':
    main()
