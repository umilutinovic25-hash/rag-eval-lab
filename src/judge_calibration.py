"""TPR/TNR of passage judges on labelled (question, passage) pairs.

Labels are a heuristic: a passage is positive when it comes from an expected document and contains the expected fact
(normalised as in eval_runner); every passage for a question that should be refused is negative. The pairs are the top
five baseline candidates of the seen sets, so this is calibration on seen data, not an independent test. Judges that
miss the bar remain advisory (eval-harness-first).
"""

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from . import config, llm
from .chunking import build_chunks
from .corpus import load_corpus
from .eval_runner import load_eval_set, normalise
from .retrieval import score_chunks, searchable_chunks
from .retrieval_metrics import EVAL_DIR, SEEN, SETS, apply_overrides, ranked
from .scratch import use_scratch_caches

GENERATOR_FAMILY = "qwen"
FAMILIES = {"qwen": "qwen", "gemma": "gemma", "mistral": "mistral", "llama": "llama"}


def yesno(model: str, prompt: str | None = None):
    return lambda question, passage: llm.yesno_judge(question, passage, model, prompt)


JUDGES = {
    "span-qwen": (llm.span_judge, "qwen"),
    "yesno-qwen": (yesno("qwen2.5:7b"), "qwen"),
    "yesno-gemma": (yesno("gemma3:4b"), "gemma"),
    "either (shipped)": (lambda q, p: llm.span_judge(q, p) or llm.yesno_judge(q, p, "gemma3:4b"), "qwen+gemma"),
    "fewshot-gemma": (yesno("gemma3:4b", config.RERANK_FEWSHOT_PROMPT), "gemma"),
    "yesno-mistral": (yesno("mistral:latest"), "mistral"),
    "fewshot-mistral": (yesno("mistral:latest", config.RERANK_FEWSHOT_PROMPT), "mistral"),
    "yesno-llama": (yesno("llama3.2:latest"), "llama"),
    "fewshot-llama": (yesno("llama3.2:latest", config.RERANK_FEWSHOT_PROMPT), "llama"),
}


def three_way(model: str):
    return lambda question, passage: llm.answerability_judge(question, passage, model)


def either(question, passage):
    return llm.span_judge(question, passage) or llm.yesno_judge(question, passage, "gemma3:4b")


JUDGES.update({
    "3way-gemma": (three_way("gemma3:4b"), "gemma"),
    "3way-qwen": (three_way("qwen2.5:7b"), "qwen"),
    "3way-mistral": (three_way("mistral:latest"), "mistral"),
    "3way-llama": (three_way("llama3.2:latest"), "llama"),
    "either+3way-gemma": (lambda q, p: either(q, p) or llm.answerability_judge(q, p, "gemma3:4b"), "qwen+gemma"),
    "either+3way-mistral": (lambda q, p: either(q, p) or llm.answerability_judge(q, p, "mistral:latest"), "qwen+gemma+mistral"),
    "either+3way-qwen": (lambda q, p: either(q, p) or llm.answerability_judge(q, p, "qwen2.5:7b"), "qwen+gemma"),
})


def build_pairs(sets=SEEN, depth: int = 5, yes_no_only: bool = False) -> list[dict]:
    chunks = build_chunks(load_corpus())
    pairs = []
    for name in sets:
        for item in load_eval_set(EVAL_DIR / SETS[name]):
            if yes_no_only and not llm.is_yes_no_question(item["question"]):
                continue
            candidates = ranked(item["question"], chunks)[:depth]
            cosines = dict(zip(searchable_chunks(chunks), score_chunks(item["question"], searchable_chunks(chunks))))
            top = max(cosines.values())
            for chunk in candidates:
                positive = (
                    item["expected_behaviour"] == "answer"
                    and chunk.doc_id in item["expected_doc_ids"]
                    and normalise(item["expected_fact"]) in normalise(chunk.text)
                )
                pairs.append({"set": name, "id": item["id"], "question": item["question"], "chunk_id": chunk.chunk_id,
                              "passage": chunk.text, "label": positive,
                              "gray_zone": config.RERANK_GRAY_ZONE[0] <= top < config.RERANK_GRAY_ZONE[1]})
    return pairs


def wilson(successes: int, total: int, z: float = 1.96) -> list[float]:
    if total == 0:
        return [0.0, 0.0]
    p = successes / total
    centre = (p + z * z / (2 * total)) / (1 + z * z / total)
    margin = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / (1 + z * z / total)
    return [round(centre - margin, 3), round(centre + margin, 3)]


def rates(pairs: list[dict], verdicts: list[bool]) -> dict:
    tp = sum(1 for p, v in zip(pairs, verdicts) if p["label"] and v)
    fn = sum(1 for p, v in zip(pairs, verdicts) if p["label"] and not v)
    tn = sum(1 for p, v in zip(pairs, verdicts) if not p["label"] and not v)
    fp = sum(1 for p, v in zip(pairs, verdicts) if not p["label"] and v)
    return {"pairs": len(pairs), "tp": tp, "fn": fn, "tn": tn, "fp": fp,
            "tpr": round(tp / (tp + fn), 3) if tp + fn else None, "tpr_ci95": wilson(tp, tp + fn),
            "tnr": round(tn / (tn + fp), 3) if tn + fp else None, "tnr_ci95": wilson(tn, tn + fp)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--judges", nargs="+", default=list(JUDGES), choices=list(JUDGES))
    parser.add_argument("--yes-no-only", action="store_true", help="only questions in yes/no form")
    parser.add_argument("--scratch", type=Path, default=Path("results/scratch"))
    args = parser.parse_args()

    use_scratch_caches(args.scratch)
    pairs = build_pairs(yes_no_only=args.yes_no_only)
    report = {"created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "pairs": len(pairs),
              "positives": sum(p["label"] for p in pairs), "generator_family": GENERATOR_FAMILY, "judges": {}}
    for name in args.judges:
        judge, family = JUDGES[name]
        verdicts = [bool(judge(p["question"], p["passage"])) for p in pairs]
        gray = [(p, v) for p, v in zip(pairs, verdicts) if p["gray_zone"]]
        report["judges"][name] = {
            "family": family, "different_family_from_generator": GENERATOR_FAMILY not in family,
            "all_pairs": rates(pairs, verdicts),
            "gray_zone_pairs": rates([p for p, _ in gray], [v for _, v in gray]),
            "false_negatives": [f"{p['set']}:{p['id']}:{p['chunk_id']}" for p, v in zip(pairs, verdicts) if p["label"] and not v],
        }
        r = report["judges"][name]["all_pairs"]
        print(f"{name:<18} TPR={r['tpr']} {r['tpr_ci95']}  TNR={r['tnr']} {r['tnr_ci95']}  FN={r['fn']} FP={r['fp']}", flush=True)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
