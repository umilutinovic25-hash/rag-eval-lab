"""Paired comparison of two candidate runs on the same question set: win/loss counts, exact McNemar and Wilson interval.

Reads candidate_runner reports (evidence/upgrade/*.json). Only questions whose outcome differs (discordant pairs)
carry information about a change; a score difference alone does not say which questions moved.

    python scripts/paired_test.py                      # the comparisons reported in REPORT_BEFORE_AFTER.md section 18
    python scripts/paired_test.py A.json cand_a B.json cand_b set
"""

import json
import sys
from math import comb, sqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UP = ROOT / "evidence" / "upgrade"

# (label, before file, before candidate, after file, after candidate, set)
COMPARISONS = [
    ("yes/no judge, test 3", "yesno3.json", "shipped", "yesno3.json", "yesno3-union", "test3"),
    ("yes/no judge, test 4", "test4-before.json", "before-yesno3", "test4-union.json", "yesno3-union", "test4"),
    ("yes/no judge, test 5", "test5-before.json", "before-yesno3", "test5-shipped.json", "shipped", "test5"),
    ("headers + judge vs neither, test 5", "test5-before.json", "previous", "test5-shipped.json", "shipped", "test5"),
]


def outcomes(file: str, candidate: str, set_name: str) -> dict[str, bool]:
    data = json.loads((UP / file).read_text())
    rows = data["candidates"][candidate]["sets"][set_name]["results"]
    return {row["id"]: bool(row["pass"]) for row in rows}


def mcnemar_exact(fixed: int, broken: int) -> float:
    """Two-sided exact binomial test on the discordant pairs (H0: fixed and broken equally likely)."""
    n = fixed + broken
    if n == 0:
        return 1.0
    k = min(fixed, broken)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2**n)


def wilson(passed: int, total: int, z: float = 1.96) -> tuple[float, float]:
    p = passed / total
    centre = (p + z * z / (2 * total)) / (1 + z * z / total)
    half = z * sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / (1 + z * z / total)
    return centre - half, centre + half


def compare(before: dict[str, bool], after: dict[str, bool]) -> dict:
    ids = sorted(before.keys() & after.keys())
    fixed = [i for i in ids if not before[i] and after[i]]
    broken = [i for i in ids if before[i] and not after[i]]
    return {
        "n": len(ids),
        "before": sum(before[i] for i in ids),
        "after": sum(after[i] for i in ids),
        "fixed": fixed,
        "broken": broken,
        "p": mcnemar_exact(len(fixed), len(broken)),
    }


def line(label: str, r: dict) -> str:
    low, high = wilson(r["after"], r["n"])
    return (f"{label}: {r['before']}/{r['n']} -> {r['after']}/{r['n']} (95% Wilson {low:.2f}-{high:.2f}); "
            f"fixed {len(r['fixed'])} {r['fixed']}, broken {len(r['broken'])} {r['broken']}; McNemar exact p={r['p']:.3f}")


def main() -> None:
    if len(sys.argv) == 6:
        a_file, a_cand, b_file, b_cand, set_name = sys.argv[1:]
        print(line(set_name, compare(outcomes(a_file, a_cand, set_name), outcomes(b_file, b_cand, set_name))))
        return
    for label, a_file, a_cand, b_file, b_cand, set_name in COMPARISONS:
        print(line(label, compare(outcomes(a_file, a_cand, set_name), outcomes(b_file, b_cand, set_name))))
    print("note: the yes/no judge was designed on the test 3 failures (V21, V25), so test 3 is not independent evidence "
          "for it and must not be pooled; test 5 is the only blind comparison")


if __name__ == "__main__":
    main()
