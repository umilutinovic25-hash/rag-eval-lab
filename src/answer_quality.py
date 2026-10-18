"""Answer-text quality, measured separately from the eval metrics.

For every supported question that was answered: does the answer text contain the
expected fact, do all [chunk-id] markers in it point at cited chunks, and which
content words appear in neither the cited chunks nor the question (a rough signal
of unsupported detail; synonyms count too, so flagged answers are reviewed by hand)?
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
WORD_RE = re.compile(r"[a-z0-9:]+")
STOPWORDS = set(
    "a an the is are be to of in on for and or with your you i my can do does it this that as by at from up per "
    "not no yes must should will may any there their they we our was were has have had been which what who when "
    "where how than then also into about after before same only".split()
)
SETS = {"eval": EVAL_SET_PATH, "holdout": HOLDOUT_SET_PATH, "test": TEST_SET_PATH}


def unsupported_words(answer: str, sources: list[str]) -> list[str]:
    known = set(WORD_RE.findall(" ".join(sources).lower()))
    words = WORD_RE.findall(MARKER_RE.sub(" ", answer.lower()))
    return [
        word
        for word in words
        if word not in STOPWORDS and len(word) > 2 and not {word, word.rstrip("s"), word + "s"} & known
    ]


def score_answer(answer: str, citations: list[str], expected_fact: str, sources: list[str] | None = None) -> dict:
    markers = MARKER_RE.findall(answer)
    return {
        "fact_in_answer": normalise(expected_fact) in normalise(answer),
        "markers_valid": bool(markers) and set(markers) <= set(citations),
        "unsupported_words": unsupported_words(answer, sources or []),
    }


def run(path: Path) -> dict:
    chunks = build_chunks(load_corpus())
    text_by_id = {chunk.chunk_id: chunk.text for chunk in chunks}
    rows = []
    for item in load_eval_set(path):
        if item["expected_behaviour"] != "answer":
            continue
        result = build_grounded_answer(item["question"], chunks)
        if result.refused:
            continue
        row = {"id": item["id"], "answer": result.answer, "citations": result.citations}
        sources = [text_by_id[chunk_id] for chunk_id in result.citations] + [item["question"]]
        row.update(score_answer(result.answer, result.citations, item["expected_fact"], sources))
        rows.append(row)
    return {
        "answer_mode": config.ANSWER_MODE,
        "answered_supported": len(rows),
        "fact_in_answer": sum(row["fact_in_answer"] for row in rows),
        "markers_valid": sum(row["markers_valid"] for row in rows),
        "with_unsupported_words": sum(bool(row["unsupported_words"]) for row in rows),
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
        if row["unsupported_words"]:
            flags += f" new={','.join(row['unsupported_words'])}"
        print(f"{row['id']:<4} {flags}  {row['answer'].replace(chr(10), ' ')[:110]}")
    n = report["answered_supported"]
    print(
        f"\n{args.set} ({report['answer_mode']}): fact in answer {report['fact_in_answer']}/{n}, "
        f"valid markers {report['markers_valid']}/{n}, with unsupported words {report['with_unsupported_words']}/{n}"
    )
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
