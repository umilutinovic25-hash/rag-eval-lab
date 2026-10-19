import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from paired_test import compare, mcnemar_exact, wilson  # noqa: E402


def test_mcnemar_exact_values():
    assert mcnemar_exact(0, 0) == 1.0
    assert mcnemar_exact(3, 0) == 0.25
    assert mcnemar_exact(5, 0) == 0.0625
    assert mcnemar_exact(4, 4) == 1.0


def test_compare_counts_only_discordant_pairs():
    r = compare({"a": False, "b": True, "c": True}, {"a": True, "b": True, "c": False})
    assert r["fixed"] == ["a"] and r["broken"] == ["c"] and r["before"] == 2 and r["after"] == 2


def test_wilson_interval_bounds():
    low, high = wilson(39, 40)
    assert 0.86 < low < 0.88 and 0.99 < high <= 1.0
