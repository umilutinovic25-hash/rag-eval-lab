"""Freeze check for the question sets: fails when a committed set, corpus or label file changed after it was recorded.

    python scripts/check_sets.py            # verify against evidence/upgrade/set-hashes.json
    python scripts/check_sets.py --write    # record the current hashes (only when a set was added on purpose)

Also reports questions that appear in more than one set (a blind set must not repeat a seen question).
"""

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "eval"
MANIFEST = ROOT / "evidence" / "upgrade" / "set-hashes.json"
# Known repeats recorded in REPORT_BEFORE_AFTER.md section 18 (test 5 reused four seen questions by mistake).
KNOWN_DUPLICATES = {("holdout:H10", "test5:X12"), ("holdout:H28", "test5:X32"), ("test2:U13", "test5:X15"), ("test4:W18", "test5:X16")}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def duplicates() -> list[tuple[str, str]]:
    seen, found = {}, []
    for path in sorted(EVAL.glob("*_set.json")):
        for item in json.loads(path.read_text()):
            key = " ".join(item["question"].lower().split())
            name = f"{path.stem.removesuffix('_set')}:{item['id']}"
            if key in seen and seen[key].split(":")[0] != name.split(":")[0]:
                found.append((seen[key], name))
            seen.setdefault(key, name)
    return found


def main() -> int:
    files = sorted(p for p in EVAL.glob("*.json"))
    current = {p.name: digest(p) for p in files}
    if "--write" in sys.argv:
        MANIFEST.write_text(json.dumps(current, indent=1) + "\n")
        print(f"recorded {len(current)} files")
        return 0
    recorded = json.loads(MANIFEST.read_text())
    problems = [f"changed: {n}" for n in recorded if n in current and current[n] != recorded[n]]
    problems += [f"missing: {n}" for n in recorded if n not in current]
    problems += [f"unrecorded: {n} (run with --write if it is a new set)" for n in current if n not in recorded]
    problems += [f"duplicate question: {a} = {b}" for a, b in duplicates() if (a, b) not in KNOWN_DUPLICATES]
    for line in problems:
        print(line)
    print("sets OK" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
