"""Run the holdout set with the same metric code as the fixed eval set.

The holdout questions were written after the thresholds were calibrated on
eval/eval_set.json, so they check whether those choices generalise.
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .chunking import build_chunks
from .corpus import load_corpus
from .eval_runner import eval_set_sha256, evaluate_item, format_table, load_eval_set, summarise
from .rag import build_grounded_answer


HOLDOUT_SET_PATH = Path(__file__).resolve().parents[1] / "eval" / "holdout_set.json"
TEST_SET_PATH = HOLDOUT_SET_PATH.with_name("test_set.json")  # blind for B1-B3, seen after that
TEST2_SET_PATH = HOLDOUT_SET_PATH.with_name("test2_set.json")  # blind for B4-B5, run once at the very end


def run_holdout(path: Path = HOLDOUT_SET_PATH) -> dict:
    chunks = build_chunks(load_corpus())
    chunks_by_id = {chunk.chunk_id: chunk for chunk in chunks}
    rows = [
        evaluate_item(item, build_grounded_answer(item["question"], chunks), chunks_by_id)
        for item in load_eval_set(path)
    ]
    return {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "eval_set_sha256": eval_set_sha256(path),
        "config": config.snapshot(),
        "summary": summarise(rows),
        "results": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the holdout set (same metrics as eval_runner)")
    parser.add_argument("--out", required=True, help="Path of the JSON run file, e.g. results/holdout.json")
    parser.add_argument("--set", default=str(HOLDOUT_SET_PATH), help="Question set to run")
    args = parser.parse_args()

    run = run_holdout(Path(args.set))
    print(format_table(run))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(run, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
