"""Ranking metrics for retrieval alone: no judge, no generation, no LLM calls beyond uncached embeddings.

Relevance has two levels. Document level: the chunk belongs to an expected document. Fact level: the chunk text
contains the expected fact (the same normalisation as eval_runner). Only questions that should be answered count.
"""

import argparse
import ast
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .chunking import Chunk, build_chunks
from .corpus import load_corpus
from .eval_runner import load_eval_set, normalise
from .retrieval import score_chunks, searchable_chunks, sort_keys
from .scratch import use_scratch_caches

EVAL_DIR = Path(__file__).resolve().parents[1] / "eval"
SETS = {"eval": "eval_set.json", "holdout": "holdout_set.json", "test": "test_set.json", "test2": "test2_set.json",
        "test3": "test3_set.json", "test4": "test4_set.json", "test5": "test5_set.json", "inject": "inject_set.json", "test6": "test6_set.json", "inject2": "inject2_set.json"}
SETS.update({name: f"{name}_set.json" for name in ("test7", "near3", "implicit3", "inject3")})
SETS["jev"] = "jev_set.json"
SETS.update({"history": "history_set.json", "history2": "history2_set.json", "history3": "history3_set.json", "history4": "history4_set.json", "present": "present_set.json", "present2": "present2_set.json", "inject4": "inject4_set.json"})
CORPORA = {"test6": "corpus2.json", "test7": "corpus2.json", "jev": "corpus2.json", "history2": "corpus2.json", "history3": "corpus2.json", "present2": "corpus2.json"}  # default: handbook
SEEN = ("eval", "holdout", "test", "test2", "test3", "test4")  # historical default selection; every registered set is now seen
KS = (1, 2, 3, 5)

VARIANTS = {
    "baseline": {},
    "headers": {"CHUNK_HEADERS": True},
    "bm25": {"RETRIEVAL_MODE": "bm25"},
    "hybrid-bm25-0.3": {"RETRIEVAL_MODE": "hybrid-bm25", "HYBRID_WEIGHT": 0.3},
    "hybrid-bm25-0.5": {"RETRIEVAL_MODE": "hybrid-bm25", "HYBRID_WEIGHT": 0.5},
    "hybrid-bm25-0.7": {"RETRIEVAL_MODE": "hybrid-bm25", "HYBRID_WEIGHT": 0.7},
    "headers+hybrid-bm25-0.5": {"CHUNK_HEADERS": True, "RETRIEVAL_MODE": "hybrid-bm25", "HYBRID_WEIGHT": 0.5},
    "hybrid-rrf": {"RETRIEVAL_MODE": "hybrid"},
}


def ranked(question: str, chunks: list[Chunk]) -> list[Chunk]:
    """All searchable chunks, best first, with the same tie-break as retrieve_top_k."""
    candidates = searchable_chunks(chunks, question)
    scores = score_chunks(question, candidates)
    keys = sort_keys(question, candidates, scores)
    order = sorted(range(len(candidates)), key=lambda i: (-keys[i], candidates[i].chunk_id))
    return [candidates[i] for i in order]


def item_metrics(item: dict, ordering: list[Chunk]) -> dict:
    docs = set(item["expected_doc_ids"])
    fact = normalise(item["expected_fact"])
    doc_flags = [chunk.doc_id in docs for chunk in ordering]
    fact_flags = [chunk.doc_id in docs and fact in normalise(chunk.text) for chunk in ordering]
    total_facts = sum(fact_flags)
    first = next((rank for rank, flag in enumerate(fact_flags, 1) if flag), None)
    ideal = sum(1 / math.log2(rank + 1) for rank in range(1, min(total_facts, 5) + 1))
    gain = sum(1 / math.log2(rank + 1) for rank, flag in enumerate(fact_flags[:5], 1) if flag)
    return {
        "id": item["id"], "category": item["category"], "first_fact_rank": first,
        "mrr": 1 / first if first else 0.0,
        "ndcg5": gain / ideal if ideal else 0.0,
        **{f"doc_hit@{k}": any(doc_flags[:k]) for k in KS},
        **{f"fact_recall@{k}": sum(fact_flags[:k]) / total_facts if total_facts else 0.0 for k in KS},
    }


def run_variant(sets: list[str], chunks: list[Chunk]) -> dict:
    rows = {}
    for name in sets:
        for item in load_eval_set(EVAL_DIR / SETS[name]):
            if item["expected_behaviour"] == "answer":
                rows[f"{name}:{item['id']}"] = item_metrics(item, ranked(item["question"], chunks))
    return rows


def aggregate(rows: dict) -> dict:
    values = list(rows.values())
    if not values:
        return {"questions": 0}
    mean = lambda key: round(sum(float(v[key]) for v in values) / len(values), 4)
    out = {"questions": len(values), "mrr": mean("mrr"), "ndcg5": mean("ndcg5")}
    for k in KS:
        out[f"doc_hit@{k}"] = mean(f"doc_hit@{k}")
        out[f"fact_recall@{k}"] = mean(f"fact_recall@{k}")
    out["fact_rank_gt2"] = sorted(key for key, v in rows.items() if v["first_fact_rank"] is None or v["first_fact_rank"] > 2)
    return out


def apply_overrides(overrides: dict) -> dict:
    previous = {key: getattr(config, key) for key in overrides}
    for key, value in overrides.items():
        setattr(config, key, value)
    return previous


def format_table(report: dict) -> str:
    columns = ["mrr", "ndcg5", "doc_hit@1", "doc_hit@2", "fact_recall@1", "fact_recall@2", "fact_recall@3", "fact_recall@5"]
    lines = [f"{'variant':<26}{'n':>4} " + " ".join(f"{c:>13}" for c in columns)]
    for name, summary in report["variants"].items():
        lines.append(f"{name:<26}{summary['questions']:>4} " + " ".join(f"{summary[c]:>13.4f}" for c in columns))
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--sets", nargs="+", default=list(SEEN), choices=list(SETS))
    parser.add_argument("--variants", nargs="+", default=list(VARIANTS), choices=list(VARIANTS))
    parser.add_argument("--scratch", type=Path, default=Path("results/scratch"))
    parser.add_argument("--set", dest="extra", action="append", default=[], metavar="KEY=VALUE",
                        help="extra config override applied to every variant")
    args = parser.parse_args()

    use_scratch_caches(args.scratch)
    chunks = build_chunks(load_corpus())
    extra = {key: ast.literal_eval(value) for key, value in (item.split("=", 1) for item in args.extra)}
    report = {"created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "sets": args.sets,
              "extra_overrides": extra, "variants": {}, "rows": {}}
    for name in args.variants:
        previous = apply_overrides({**VARIANTS[name], **extra})
        try:
            rows = run_variant(args.sets, chunks)
        finally:
            apply_overrides(previous)
        report["variants"][name] = aggregate(rows)
        report["rows"][name] = rows
    print(format_table(report))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
