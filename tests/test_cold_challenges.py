import pytest
from scripts.compare_cold_challenges import compare


def report(passed=True, citations=None):
    return {'sets': {'s': {'results': [{'id': '1', 'pass': passed, 'cited_chunk_ids': citations or []}]}}}


def test_cold_comparison_checks_pass_and_ordered_citations():
    assert compare(report(), report()) == []
    assert len(compare(report(), report(False))) == 1
    assert len(compare(report(citations=['a', 'b']), report(citations=['b', 'a']))) == 1
    with pytest.raises(ValueError):
        compare(report(), {'sets': {}})
