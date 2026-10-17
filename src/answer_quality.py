"""Answer-text quality, measured separately from the eval metrics.

For every supported question that was answered: does the answer text contain the
expected fact, and do all [chunk-id] markers in it point at cited chunks?
"""

import argparse
import json
import re
from pathlib import Path

from . import config
from .chunking import build_chunks
from .corpus import load_corpus
from .eval_runner import EVAL_SET_PATH, load_eval_set, normalise
from .holdout_runner import HOLDOUT_SET_PATH, TEST_SET_PATH
from .rag import build_grounded_answer

MARKER_RE = re.compile(r"\[([a-z0-9-]+-chunk-\d+)\]")
SETS = {"eval": EVAL_SET_PATH, "holdout": HOLDOUT_SET_PATH, "test": TEST_SET_PATH}


def score_answer(answer: str, citations: list[str], expected_fact: str) -> dict:
    markers = MARKER_RE.findall(answer)
    return {
        "fact_in_answer": normalise(expected_fact) in normalise(answer),
        "markers_valid": bool(markers) and set(markers) <= set(citations),
    }


def run(path: Path) -> dict:
    chunks = build_chunks(load_corpus())
    rows = []
    for item in load_eval_set(path):
        if item["expected_behaviour"] != "answer":
            continue
        result = build_grounded_answer(item["question"], chunks)
        if result.refused:
            continue
        row = {"id": item["id"], "answer": result.answer, "citations": result.citations}
        row.update(score_answer(result.answer, result.citations, item["expected_fact"]))
        rows.append(row)
    return {
        "answer_mode": config.ANSWER_MODE,
        "answered_supported": len(rows),
        "fact_in_answer": sum(row["fact_in_answer"] for row in rows),
        "markers_valid": sum(row["markers_valid"] for row in rows),
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure answer text quality (fact present, citation markers valid)")
    parser.add_argument("--set", choices=sorted(SETS), default="eval")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    report = run(SETS[args.set])
    for row in report["rows"]:
        flags = f"fact={'yes' if row['fact_in_answer'] else 'no '} markers={'ok ' if row['markers_valid'] else 'bad'}"
        print(f"{row['id']:<4} {flags}  {row['answer'].replace(chr(10), ' ')[:110]}")
    n = report["answered_supported"]
    print(f"\n{args.set} ({report['answer_mode']}): fact in answer {report['fact_in_answer']}/{n}, valid markers {report['markers_valid']}/{n}")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
