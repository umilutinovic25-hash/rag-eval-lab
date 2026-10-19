"""Fill the human-only fields of REPORT_BEFORE_AFTER.md from values the pair provides. Nothing is invented here.

    python scripts/fill_report_fields.py --status            # list the fields that are still open
    python scripts/fill_report_fields.py --partner "Ime Prezime" --demo "Ime" --uros "..." --partner-work "..."
    python scripts/fill_report_fields.py --reviewer "Ime" --q1 "..." --q2 "..." --q3 "..." --reply "..."
    python scripts/fill_report_fields.py --manual-checks "..."

Each option replaces its placeholder only when given; run it as many times as values arrive. Use --dry-run to preview.
"""

import argparse
import re
import sys
from pathlib import Path

REPORT = Path(__file__).resolve().parents[1] / "REPORT_BEFORE_AFTER.md"

# option -> (placeholder as written in the report, whether it may occur more than once)
FIELDS = {
    "partner": ("[drugi član para]", True),
    "demo": ("[ime]", False),
    "reviewer": ("[par / imena]", False),
    "q1": ("1. Da li je promena zaista jedna i da li odgovara specifikaciji? [odgovor]", False),
    "q2": ("2. Da li rezultat pre/posle podržava zaključak? [odgovor]", False),
    "q3": ("3. Da li je neka regresija ili ograničenje izostavljeno? [odgovor]", False),
    "reply": ("[šta smo promenili ili zašto nismo]", False),
    "manual_checks": ("[Dopuniti: šta je svako od nas ručno proverio.]", False),
}
OPEN = re.compile(r"\[(?:drugi član para|ime|par / imena|odgovor|šta smo promenili ili zašto nismo|dopuniti|Dopuniti[^\]]*)\]")


def apply(text: str, values: dict[str, str]) -> str:
    for key, value in values.items():
        if key not in FIELDS:
            continue
        placeholder, _ = FIELDS[key]
        if key in ("q1", "q2", "q3"):
            head = placeholder.replace(" [odgovor]", "")
            text = text.replace(placeholder, f"{head} {value}", 1)
        else:
            text = text.replace(placeholder, value)
    if values.get("uros"):
        text = text.replace("| Uroš Milutinović | [dopuniti] |", f"| Uroš Milutinović | {values['uros']} |", 1)
    if values.get("partner_work"):
        row = re.search(r"\| (?!Uroš)([^|\n]+) \| \[dopuniti\] \|", text)
        if row:
            text = text.replace(row[0], f"| {row[1]} | {values['partner_work']} |", 1)
    return text


def status(text: str) -> list[str]:
    return [f"line {i}: {line.strip()[:110]}" for i, line in enumerate(text.splitlines(), 1) if OPEN.search(line)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for key in list(FIELDS) + ["uros", "partner_work"]:
        parser.add_argument("--" + key.replace("_", "-"), dest=key)
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    text = REPORT.read_text()
    if args.status:
        left = status(text)
        print("\n".join(left) if left else "no open fields")
        return 0
    values = {k: v for k, v in vars(args).items() if k in list(FIELDS) + ["uros", "partner_work"] and v}
    if not values:
        parser.print_help()
        return 2
    new = apply(text, values)
    if args.dry_run:
        print("\n".join(status(new)) or "no open fields")
        return 0
    REPORT.write_text(new)
    print("updated; still open:", len(status(new)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
