"""Compare a person's review (review/human-review.html export) with the AI-written yes/no labels and the system's answers.

    python -m src.human_agreement human-review.json --out evidence/upgrade/human-agreement.json

Reports how many answers the person judged correct, and for yes/no answers whether the system's leading yes/no matches the
AI label and whether the person agrees with the AI label (Cohen kappa between the person's verdict and the AI's).
"""

import argparse
import json
from pathlib import Path

from .polarity import LABELS, leading_verdict


def kappa(pairs: list[tuple[str, str]]) -> float | None:
    n = len(pairs)
    if not n:
        return None
    classes = sorted({x for p in pairs for x in p})
    observed = sum(a == b for a, b in pairs) / n
    expected = sum((sum(a == c for a, _ in pairs) / n) * (sum(b == c for _, b in pairs) / n) for c in classes)
    return None if expected == 1 else round((observed - expected) / (1 - expected), 3)


def analyse(review: dict, answers: list[dict]) -> dict:
    labels = json.loads(LABELS.read_text())["labels"]
    verdicts = {k: v["v"] for k, v in review.get("answers", {}).items() if v.get("v")}
    by_id = {a["id"]: a for a in answers}
    judged = [i for i in verdicts if i in by_id]
    ai_pairs, wrong = [], []
    for i in judged:
        set_name, qid = i.split(":")
        label = labels.get(set_name, {}).get(qid)
        lead = leading_verdict(by_id[i]["answer"])
        if label and lead:
            # the AI's view of the system answer: correct when the leading yes/no equals the AI label
            ai = "ok" if lead == label else "wrong"
            human = "ok" if verdicts[i] == "ok" else "wrong"
            ai_pairs.append((human, ai))
        if verdicts[i] == "wrong":
            wrong.append(i)
    translation = review.get("translation", {})
    return {
        "reviewer": review.get("reviewer"),
        "answers_judged": len(judged),
        "ok": sum(verdicts[i] == "ok" for i in judged),
        "wrong": wrong,
        "partial": [i for i in judged if verdicts[i] == "partial"],
        "yes_no_compared": len(ai_pairs),
        "yes_no_agreement": round(sum(a == b for a, b in ai_pairs) / len(ai_pairs), 3) if ai_pairs else None,
        "yes_no_kappa_human_vs_ai": kappa(ai_pairs),
        "translation_ok": sum(v.get("v") == "ok" for v in translation.values()),
        "translation_fix": {k: v.get("c", "") for k, v in translation.items() if v.get("v") == "fix"},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("review", type=Path)
    parser.add_argument("--answers", type=Path, default=Path("review/human-review-answers.json"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = analyse(json.loads(args.review.read_text()), json.loads(args.answers.read_text()))
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "translation_fix"}, ensure_ascii=False))
    for chunk_id, comment in report["translation_fix"].items():
        print(f"fix {chunk_id}: {comment}")


if __name__ == "__main__":
    main()
