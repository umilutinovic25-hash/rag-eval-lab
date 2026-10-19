"""Answer-level check for yes/no questions: does the answer text lead with the expected yes or no?

The pass rule of eval_runner only looks at cited chunks. This measures the generated sentence on the questions listed in
eval/polarity_labels.json (labels written by the AI assistant from the corpus, not by a human). An answer that does not
start with yes or no (an extractive fallback, a refusal) counts as no verdict, not as wrong.
"""

import argparse
import json
import re
from pathlib import Path

from . import config
from .candidate_runner import corpus_chunks
from .chunking import build_chunks
from .corpus import load_corpus
from .eval_runner import load_eval_set
from .rag import QUOTE_PREFIX, build_grounded_answer
from .retrieval_metrics import EVAL_DIR, SETS, apply_overrides
from .scratch import use_scratch_caches

LABELS = EVAL_DIR / "polarity_labels.json"


def leading_verdict(answer: str) -> str | None:
    sentence = "\n".join(line for line in answer.splitlines() if not line.startswith(QUOTE_PREFIX)).strip()
    match = re.match(r"(yes|no)\b", sentence, re.I)
    return match[1].lower() if match else None


def score(set_name: str, chunks) -> dict:
    labels = json.loads(LABELS.read_text())["labels"][set_name]
    chunks = corpus_chunks(set_name, chunks)
    rows = []
    for item in load_eval_set(EVAL_DIR / SETS[set_name]):
        if item["id"] not in labels:
            continue
        result = build_grounded_answer(item["question"], chunks)
        verdict = None if result.refused else leading_verdict(result.answer)
        outcome = "refused" if result.refused else "none" if verdict is None else "correct" if verdict == labels[item["id"]] else "wrong"
        rows.append({"id": item["id"], "expected": labels[item["id"]], "verdict": verdict, "outcome": outcome,
                     "fallback": result.generation_fallback_reason})
    counts = {k: sum(r["outcome"] == k for r in rows) for k in ("correct", "wrong", "none", "refused")}
    return {"set": set_name, "n": len(rows), **counts, "wrong_ids": [r["id"] for r in rows if r["outcome"] == "wrong"], "rows": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sets", nargs="+", default=["test3", "test4", "test5"])
    parser.add_argument("--set-config", nargs="*", default=[], help="KEY=VALUE overrides, e.g. POLARITY_CHECK=False")
    parser.add_argument("--scratch", type=Path, default=Path("results/scratch"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    use_scratch_caches(args.scratch)
    overrides = {k: json.loads(v.lower() if v in ("True", "False", "None") else v) for k, v in (a.split("=", 1) for a in args.set_config)}
    previous = apply_overrides(overrides)
    try:
        chunks = build_chunks(load_corpus())
        report = [score(name, chunks) for name in args.sets]
    finally:
        apply_overrides(previous)
    for r in report:
        print(f"{r['set']}: {r['n']} yes/no answers, correct {r['correct']}, wrong {r['wrong']} {r['wrong_ids']}, "
              f"no verdict {r['none']}, refused {r['refused']}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"overrides": overrides, "sets": report}, indent=2) + "\n")


if __name__ == "__main__":
    main()
