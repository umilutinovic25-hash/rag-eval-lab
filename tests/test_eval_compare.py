import json
import subprocess
import sys

import pytest

from src.eval_compare import MULTI_SETTING_WARNING, compare_runs


def make_run(passes: dict[str, bool], config: dict, sha: str = "abc") -> dict:
    return {
        "eval_set_sha256": sha,
        "config": config,
        "summary": {"passed": sum(passes.values()), "total": len(passes)},
        "results": [{"id": qid, "pass": ok} for qid, ok in passes.items()],
    }


def test_detects_fixed_and_regressed() -> None:
    before = make_run({"E01": True, "E02": False, "E03": True}, {"TOP_K": 2})
    after = make_run({"E01": False, "E02": True, "E03": True}, {"TOP_K": 1})
    result = compare_runs(before, after)
    assert result["fixed"] == ["E02"]
    assert result["regressed"] == ["E01"]
    assert result["unchanged"] == ["E03"]
    assert result["warning"] is None


def test_warns_when_more_than_one_setting_changed() -> None:
    before = make_run({"E01": True}, {"TOP_K": 2, "CHUNK_SIZE": 140})
    after = make_run({"E01": True}, {"TOP_K": 1, "CHUNK_SIZE": 200})
    assert compare_runs(before, after)["warning"] == MULTI_SETTING_WARNING


def test_refuses_different_eval_sets() -> None:
    with pytest.raises(ValueError):
        compare_runs(make_run({"E01": True}, {}, "abc"), make_run({"E01": True}, {}, "def"))


def test_cli_exits_1_on_hash_mismatch(tmp_path) -> None:
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    a.write_text(json.dumps(make_run({"E01": True}, {}, "abc")))
    b.write_text(json.dumps(make_run({"E01": True}, {}, "def")))
    proc = subprocess.run([sys.executable, "-m", "src.eval_compare", str(a), str(b)], capture_output=True, text=True)
    assert proc.returncode == 1
    assert "eval_set_sha256" in proc.stderr
