import hashlib
import json
from pathlib import Path
import pytest


def test_frozen_candidate_is_not_falsely_human_approved():
    path=Path('review/acceptance-v2.json')
    expected=path.with_suffix('.sha256').read_text().split()[0]
    assert hashlib.sha256(path.read_bytes()).hexdigest()==expected
    data=json.loads(path.read_text())
    assert data['reviewer'] is None
    assert data['independent_blind_evidence'] is False
    assert len(data['items'])==24
    assert len({r['pair'] for r in data['items']})==12


def test_human_review_rejects_missing_or_incomplete_decisions():
    from src.acceptance_runner import validate_review
    with pytest.raises(ValueError): validate_review({'reviewer':'','items':[]}, ['V01-en'])
    with pytest.raises(ValueError): validate_review({'reviewer':'Actual reviewer','items':[]}, ['V01-en'])
    assert validate_review({'reviewer':'Actual reviewer','items':[{'id':'V01-en','decision':'accepted','comment':'Source checked'}]},['V01-en'])=='Actual reviewer'


def test_human_review_is_bound_to_the_exact_answers():
    from src.acceptance_runner import answer_fingerprint, validate_review
    rows=[{'id':'a','result':{'answer':'Original','citations':[],'refused':False,'profile':'offline','question':'Q','seconds':1}}]
    fingerprint=answer_fingerprint(rows)
    rows[0]['result']['seconds']=2
    assert answer_fingerprint(rows)==fingerprint
    rows[0]['result']['answer']='Changed'
    assert answer_fingerprint(rows)!=fingerprint
    review={'reviewer':'Actual reviewer','answers_sha256':'different','items':[{'id':'a','decision':'accepted','comment':'Checked'}]}
    with pytest.raises(ValueError): validate_review(review,['a'],fingerprint)
