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
from .claim_checks import claim_risks
from .chunking import build_chunks
from .corpus import load_corpus
from .eval_runner import EVAL_SET_PATH, load_eval_set, normalise
from .holdout_runner import HOLDOUT_SET_PATH, TEST_SET_PATH, TEST2_SET_PATH
from .rag import QUOTE_PREFIX, build_grounded_answer

MARKER_RE = re.compile(r"\[([a-z0-9-]+-chunk-\d+)\]")
WORD_RE = re.compile(r"[a-z0-9:]+")
STOPWORDS = set(
    "a an the is are be to of in on for and or with your you i my can do does it this that as by at from up per "
    "not no yes must should will may any there their they we our was were has have had been which what who when "
    "where how than then also into about after before same only".split()
)
SETS = {"eval": EVAL_SET_PATH, "holdout": HOLDOUT_SET_PATH, "test": TEST_SET_PATH, "test2": TEST2_SET_PATH,
        "test3": TEST2_SET_PATH.with_name("test3_set.json"), "test4": TEST2_SET_PATH.with_name("test4_set.json"),
        "test5": TEST2_SET_PATH.with_name("test5_set.json")}


def model_sentence(answer: str) -> str:
    """The answer without the verbatim Source lines, i.e. only what the model wrote."""
    return "\n".join(line for line in answer.splitlines() if not line.startswith(QUOTE_PREFIX))


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


def review_flags(answer: str, passages: list[str], expected_fact: str) -> list[str]:
    """Conservative lexical warnings, not a semantic correctness verdict."""
    body = MARKER_RE.sub(" ", answer)
    flags = []
    if not set(re.findall(r"\d+(?:[.:]\d+)*", body)) <= set(re.findall(r"\d+(?:[.:]\d+)*", " ".join(passages))):
        flags.append("number_not_in_sources")
    negative = lambda text: bool(re.search(r"\b(?:no|not|never|cannot)\b|n['’]t\b", text.casefold()))
    relevant = [sentence for p in passages for sentence in re.split(r"(?<=[.!?])\s+", p)
                if expected_fact and normalise(expected_fact) in normalise(sentence)]
    if relevant and all(negative(body) != negative(sentence) for sentence in relevant):
        flags.append("negation_mismatch")
    return sorted(set(flags + claim_risks(body, passages)))


def run(path: Path) -> dict:
    chunks = build_chunks(load_corpus())
    text_by_id = {chunk.chunk_id: chunk.text for chunk in chunks}
    rows = []
    for item in load_eval_set(path):
        result = build_grounded_answer(item["question"], chunks)
        expects_answer = item["expected_behaviour"] == "answer"
        fact = item["expected_fact"] or ""
        sentence = model_sentence(result.answer)
        passages = [text_by_id[c] for c in result.citations]
        row = {
            "id": item["id"], "question": item["question"], "expected": item["expected_behaviour"],
            "refused": result.refused, "answer": result.answer, "citations": result.citations,
            "expected_fact": item["expected_fact"], "semantic_correctness": "not_assessed",
            "review_required": True, "generation_fallback_reason": result.generation_fallback_reason,
        }
        row.update(score_answer(sentence, result.citations, fact, passages + [item["question"]]))
        row["fact_in_answer"] = bool(fact) and not result.refused and row["fact_in_answer"]
        row["fact_in_full_answer"] = bool(fact) and not result.refused and normalise(fact) in normalise(result.answer)
        row["review_flags"] = review_flags(sentence, passages, fact) if not result.refused else []
        if expects_answer and result.refused:
            row["review_flags"].append("false_refusal")
        elif not expects_answer and not result.refused:
            row["review_flags"].append("unsupported_answer")
        if not result.refused and not row["markers_valid"]:
            row["review_flags"].append("invalid_marker")
        rows.append(row)
    supported = [row for row in rows if row["expected"] == "answer"]
    answered = [row for row in supported if not row["refused"]]
    return {
        "answer_mode": config.ANSWER_MODE, "total_questions": len(rows),
        "supported_total": len(supported), "answered_supported": len(answered),
        "supported_answer_coverage": len(answered) / len(supported) if supported else None,
        "false_refusals": len(supported) - len(answered),
        "unsupported_answers": sum(row["expected"] == "refuse" and not row["refused"] for row in rows),
        "fact_in_answer": sum(row["fact_in_answer"] for row in answered),
        "markers_valid": sum(row["markers_valid"] for row in answered),
        "with_unsupported_words": sum(bool(row["unsupported_words"]) for row in answered),
        "fact_in_full_answer": sum(row["fact_in_full_answer"] for row in answered),
        "semantic_correctness": "not_assessed; lexical signals require independent review",
        "rows_with_review_flags": sum(bool(row["review_flags"]) for row in rows),
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure answer text quality (fact present, citation markers valid)")
    parser.add_argument("--set", choices=sorted(SETS), default="eval")
    parser.add_argument("--out", required=True)
    parser.add_argument("--scratch", help="run against copies of the caches in this directory (committed caches stay untouched)")
    args = parser.parse_args()
    if args.scratch:
        from .scratch import use_scratch_caches
        use_scratch_caches(Path(args.scratch))
    report = run(SETS[args.set])
    for row in report["rows"]:
        flags = f"fact={'yes' if row['fact_in_answer'] else 'no '} markers={'ok ' if row['markers_valid'] else 'bad'}"
        if row["unsupported_words"]:
            flags += f" new={','.join(row['unsupported_words'])}"
        flags += " review=" + ",".join(row["review_flags"])
        print(f"{row['id']:<4} {flags}  {row['answer'].replace(chr(10), ' ')[:110]}")
    n = report["answered_supported"]
    print(f"Coverage: {n}/{report['supported_total']}; false refusals: {report['false_refusals']}; unsupported answers: {report['unsupported_answers']}")
    print("Semantic correctness: NOT ASSESSED. Lexical signals and marker checks are not a truth verdict.")
    print(
        f"\n{args.set} ({report['answer_mode']}): fact in answer {report['fact_in_answer']}/{n}, "
        f"valid markers {report['markers_valid']}/{n}, with unsupported words {report['with_unsupported_words']}/{n} "
        f"(model sentence); fact in full answer {report['fact_in_full_answer']}/{n}"
    )
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
