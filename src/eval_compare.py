import argparse
import json
import sys
from pathlib import Path


MULTI_SETTING_WARNING = "More than one setting changed: the difference may not be attributable to one change."


def load_run(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def compare_runs(before: dict, after: dict) -> dict:
    if before["eval_set_sha256"] != after["eval_set_sha256"]:
        raise ValueError("The two runs used different eval sets (eval_set_sha256 differs). Comparison refused.")

    before_rows = {row["id"]: row for row in before["results"]}
    after_rows = {row["id"]: row for row in after["results"]}
    fixed, regressed, unchanged = [], [], []
    for qid in before_rows:
        was, now = before_rows[qid]["pass"], after_rows[qid]["pass"]
        if not was and now:
            fixed.append(qid)
        elif was and not now:
            regressed.append(qid)
        else:
            unchanged.append(qid)

    deltas = {}
    for key, old in before["summary"].items():
        new = after["summary"][key]
        if isinstance(old, (int, float)) and isinstance(new, (int, float)):
            deltas[key] = round(new - old, 4)

    keys = sorted(set(before["config"]) | set(after["config"]))
    changed = {
        key: (before["config"].get(key), after["config"].get(key))
        for key in keys
        if before["config"].get(key) != after["config"].get(key)
    }
    return {
        "fixed": fixed,
        "regressed": regressed,
        "unchanged": unchanged,
        "summary_delta": deltas,
        "changed_settings": changed,
        "warning": MULTI_SETTING_WARNING if len(changed) > 1 else None,
    }


def format_comparison(comparison: dict, before: dict, after: dict) -> str:
    lines = [
        f"Fixed (fail -> pass): {', '.join(comparison['fixed']) or 'none'}",
        f"Regressed (pass -> fail): {', '.join(comparison['regressed']) or 'none'}",
        f"Unchanged: {', '.join(comparison['unchanged']) or 'none'}",
        "",
        "Summary:",
    ]
    for key, delta in comparison["summary_delta"].items():
        lines.append(f"  {key}: {before['summary'][key]} -> {after['summary'][key]} ({delta:+})")
    lines += ["", "Changed settings:"]
    if not comparison["changed_settings"]:
        lines.append("  none")
    for key, (old, new) in comparison["changed_settings"].items():
        lines.append(f"  {key}: {old!r} -> {new!r}")
    if comparison["warning"]:
        lines += ["", f"WARNING: {comparison['warning']}"]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare two eval runs")
    parser.add_argument("before")
    parser.add_argument("after")
    args = parser.parse_args()

    before, after = load_run(args.before), load_run(args.after)
    try:
        comparison = compare_runs(before, after)
    except ValueError as error:
        print(error, file=sys.stderr)
        sys.exit(1)
    print(format_comparison(comparison, before, after))


if __name__ == "__main__":
    main()
