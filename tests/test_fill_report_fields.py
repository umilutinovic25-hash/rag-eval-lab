import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from fill_report_fields import apply, status  # noqa: E402

SAMPLE = """**Par:** Uroš i [drugi član para]
**Demonstraciju vodi:** [ime]
1. Da li je promena zaista jedna i da li odgovara specifikaciji? [odgovor]

| Uroš Milutinović | [dopuniti] |
| [drugi član para] | [dopuniti] |
"""


def test_apply_fills_only_given_fields():
    out = apply(SAMPLE, {"partner": "Ana", "demo": "Uroš"})
    assert "Uroš i Ana" in out and "vodi:** Uroš" in out
    assert "[odgovor]" in out and "[dopuniti]" in out


def test_contribution_rows_and_answers():
    out = apply(SAMPLE, {"partner": "Ana", "uros": "RAG kod", "partner_work": "pregled", "q1": "Da."})
    assert "| Uroš Milutinović | RAG kod |" in out and "| Ana | pregled |" in out
    assert "specifikaciji? Da." in out
    assert status(out) == []
