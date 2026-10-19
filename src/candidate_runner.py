"""Run whole-pipeline candidates on the seen sets (and optionally the blind test 3) with scratch caches.

Reports pass counts, mean citation precision, generation fallbacks and request counts per set, so a candidate can be
checked against the acceptance rule in docs/rag-upgrade-spec.md.
"""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from . import config, operation
from .chunking import build_chunks
from .corpus import Document, load_corpus
from .eval_runner import evaluate_item, load_eval_set, summarise
from .rag import build_grounded_answer
from .retrieval_metrics import CORPORA, EVAL_DIR, SEEN, SETS, apply_overrides
from .scratch import use_scratch_caches

CANDIDATES = {
    "shipped": {},
    "previous": {"CHUNK_HEADERS": False, "YESNO_QUESTION_JUDGE": None},
    "before-yesno3": {"YESNO_QUESTION_JUDGE": None},
    "headers": {"CHUNK_HEADERS": True},
    "fewshot": {"RERANK_JUDGE": "fewshot"},
    "json": {"ANSWER_FORMAT": "json"},
    "mistral-judge": {"RERANK_JUDGE": "yesno", "RERANK_MODEL": "mistral:latest"},
    "headers+fewshot": {"CHUNK_HEADERS": True, "RERANK_JUDGE": "fewshot"},
    "headers+json": {"CHUNK_HEADERS": True, "ANSWER_FORMAT": "json"},
    "yesno3-union": {"YESNO_QUESTION_JUDGE": "answerability"},
    "yesno3-only": {"YESNO_QUESTION_JUDGE": "answerability-only"},
    "yesno3-union-qwen": {"YESNO_QUESTION_JUDGE": "answerability", "YESNO_QUESTION_MODEL": "qwen2.5:7b"},
    "no-numbers-from-question": {"NUMBERS_FROM_QUESTION": False},
    "no-polarity-check": {"POLARITY_CHECK": False},
    "no-injection-guards": {"INJECTION_GUARDS": False},
    "no-evidence-rules": {"EVIDENCE_RULES_ENABLED": False},
    "top_k=1": {"TOP_K": 1},
    "top_k=3": {"TOP_K": 3},
}


def corpus_chunks(name: str, default):
    if name not in CORPORA:
        return default
    return build_chunks([Document(**doc) for doc in json.loads((EVAL_DIR / CORPORA[name]).read_text())])


def run_set(name: str, chunks) -> dict:
    chunks = corpus_chunks(name, chunks)
    by_id = {chunk.chunk_id: chunk for chunk in chunks}
    rows, fallbacks = [], {}
    started = time.perf_counter()
    for item in load_eval_set(EVAL_DIR / SETS[name]):
        result = build_grounded_answer(item["question"], chunks)
        row = evaluate_item(item, result, by_id)
        rows.append(row)
        if result.generation_fallback_reason:
            fallbacks[item["id"]] = result.generation_fallback_reason
    return {
        "summary": summarise(rows),
        "failed": [row["id"] for row in rows if not row["pass"]],
        "fallbacks": fallbacks,
        "seconds": round(time.perf_counter() - started, 1),
        "results": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--candidates", nargs="+", default=list(CANDIDATES), choices=list(CANDIDATES))
    parser.add_argument("--sets", nargs="+", default=list(SEEN), choices=list(SETS))
    parser.add_argument("--scratch", type=Path, default=Path("results/scratch"))
    args = parser.parse_args()

    use_scratch_caches(args.scratch)
    chunks = build_chunks(load_corpus())
    report = {"created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "sets": args.sets, "candidates": {}}
    for name in args.candidates:
        previous = apply_overrides(CANDIDATES[name])
        try:
            per_set = {}
            for set_name in args.sets:
                per_set[set_name] = run_set(set_name, chunks)
                s = per_set[set_name]
                print(f"{name:<18}{set_name:<8}{s['summary']['passed']}/{s['summary']['total']}  "
                      f"cit_prec={s['summary']['mean_citation_precision']}  failed={s['failed']}  "
                      f"fallbacks={len(s['fallbacks'])}  {s['seconds']}s", flush=True)
        finally:
            apply_overrides(previous)
        report["candidates"][name] = {"overrides": CANDIDATES[name], "sets": per_set}
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
