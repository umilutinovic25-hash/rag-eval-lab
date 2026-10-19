#!/bin/sh
# Local quality gate (GitHub Actions is locked on this account): tests, frozen question sets, paired comparison.
# The model-backed runs (candidate_runner) need Ollama and are not part of this offline gate.
set -e
cd "$(dirname "$0")/.."
. .venv/bin/activate
python -m pytest -q
python scripts/check_sets.py
python scripts/paired_test.py > /dev/null
echo "gate OK"
