import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import check_sets  # noqa: E402


def test_frozen_sets_match_manifest_and_only_known_duplicates_exist():
    assert check_sets.main.__module__ == "check_sets"
    assert set(check_sets.duplicates()) <= check_sets.KNOWN_DUPLICATES
    recorded = check_sets.MANIFEST.read_text()
    assert "test6_set.json" in recorded and "inject2_set.json" in recorded
