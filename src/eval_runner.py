import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .chunking import Chunk, build_chunks
from .corpus import load_corpus
from .rag import RagAnswer, build_grounded_answer


EVAL_SET_PATH = Path(__file__).resolve().parents[1] / "eval" / "eval_set.json"


def eval_set_sha256(path: Path = EVAL_SET_PATH) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_eval_set(path: Path = EVAL_SET_PATH) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalise(text: str) -> str:
    return " ".join(text.lower().split())


def evaluate_item(item: dict, result: RagAnswer, chunks_by_id: dict[str, Chunk]) -> dict:
    expects_answer = item["expected_behaviour"] == "answer"
    answered = not result.refused
    expected_docs = set(item["expected_doc_ids"])
    cited = [chunks_by_id[chunk_id] for chunk_id in result.citations]

    row = {
        "id": item["id"],
        "category": item["category"],
        "expected": item["expected_behaviour"],
        "got": "answer" if answered else "refuse",
        "behaviour_correct": answered == expects_answer,
        "retrieval_hit": None,
        "fact_in_citations": None,
        "citation_precision": None,
        "cited_chunk_ids": list(result.citations),
        "top_k": [
            {"chunk_id": r.chunk.chunk_id, "score": round(r.score, 6)} for r in result.retrieved
        ],
    }

    if expects_answer:
        row["retrieval_hit"] = any(r.chunk.doc_id in expected_docs for r in result.retrieved)
        fact = normalise(item["expected_fact"])
        row["fact_in_citations"] = any(fact in normalise(chunk.text) for chunk in cited)

    if answered:
        relevant = sum(1 for chunk in cited if chunk.doc_id in expected_docs)
        row["citation_precision"] = round(relevant / len(cited), 4) if cited else 0.0

    row["pass"] = bool(
        row["behaviour_correct"]
        and (
            not expects_answer
            or (row["fact_in_citations"] and row["citation_precision"] >= 0.5)
        )
    )
    return row


def summarise(rows: list[dict]) -> dict:
    supported = [row for row in rows if row["expected"] == "answer"]
    answered = [row for row in rows if row["got"] == "answer"]
    return {
        "passed": sum(1 for row in rows if row["pass"]),
        "total": len(rows),
        "behaviour_accuracy": round(sum(row["behaviour_correct"] for row in rows) / len(rows), 4),
        "retrieval_hit_rate": round(sum(row["retrieval_hit"] for row in supported) / len(supported), 4)
        if supported
        else None,
        "mean_citation_precision": round(
            sum(row["citation_precision"] for row in answered) / len(answered), 4
        )
        if answered
        else None,
    }


def run_eval() -> dict:
    chunks = build_chunks(load_corpus())
    chunks_by_id = {chunk.chunk_id: chunk for chunk in chunks}
    rows = [
        evaluate_item(item, build_grounded_answer(item["question"], chunks), chunks_by_id)
        for item in load_eval_set()
    ]
    return {
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "eval_set_sha256": eval_set_sha256(),
        "config": config.snapshot(),
        "summary": summarise(rows),
        "results": rows,
    }


def mark(value) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "yes" if value else "no"
    return f"{value:.2f}"


def format_table(run: dict) -> str:
    header = f"{'ID':<4} {'Category':<24} {'Expected':<8} {'Got':<7} {'Hit':<4} {'Fact':<5} {'CitPrec':<7} Pass"
    lines = [header, "-" * len(header)]
    for row in run["results"]:
        lines.append(
            f"{row['id']:<4} {row['category']:<24} {row['expected']:<8} {row['got']:<7} "
            f"{mark(row['retrieval_hit']):<4} {mark(row['fact_in_citations']):<5} "
            f"{mark(row['citation_precision']):<7} {'PASS' if row['pass'] else 'FAIL'}"
        )
    s = run["summary"]
    lines += [
        "",
        f"Passed: {s['passed']}/{s['total']}",
        f"Behaviour accuracy: {mark(s['behaviour_accuracy'])}",
        f"Retrieval hit rate (supported): {mark(s['retrieval_hit_rate'])}",
        f"Mean citation precision (answered): {mark(s['mean_citation_precision'])}",
        f"eval_set_sha256: {run['eval_set_sha256']}",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the fixed Week 7 eval set")
    parser.add_argument("--out", required=True, help="Path of the JSON run file, e.g. results/before.json")
    args = parser.parse_args()

    run = run_eval()
    print(format_table(run))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(run, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
