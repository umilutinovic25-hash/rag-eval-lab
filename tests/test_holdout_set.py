from src.chunking import build_chunks
from src.corpus import load_corpus
from src.eval_runner import load_eval_set, normalise
import pytest

from src.holdout_runner import HOLDOUT_SET_PATH, TEST_SET_PATH

SETS = pytest.mark.parametrize("path", [HOLDOUT_SET_PATH, TEST_SET_PATH], ids=["holdout", "test"])

CATEGORIES = {
    "supported", "paraphrase", "versioned", "near-duplicate-trap", "unsupported", "unsupported-near-domain",
}


@SETS
def test_ids_are_unique_and_questions_are_new(path) -> None:
    items = load_eval_set(path)
    assert len({item["id"] for item in items}) == len(items)
    eval_questions = {normalise(item["question"]) for item in load_eval_set()}
    assert not eval_questions & {normalise(item["question"]) for item in items}


@SETS
def test_fact_is_inside_one_current_chunk(path) -> None:
    chunks = [chunk for chunk in build_chunks(load_corpus()) if chunk.status != "superseded"]
    for item in load_eval_set(path):
        assert item["category"] in CATEGORIES
        if item["expected_behaviour"] == "refuse":
            assert item["expected_doc_ids"] == [] and item["expected_fact"] is None
            continue
        fact = normalise(item["expected_fact"])
        assert any(
            chunk.doc_id in item["expected_doc_ids"] and fact in normalise(chunk.text) for chunk in chunks
        ), item["id"]


def test_test_set_does_not_repeat_holdout_questions() -> None:
    holdout = {normalise(item["question"]) for item in load_eval_set(HOLDOUT_SET_PATH)}
    assert not holdout & {normalise(item["question"]) for item in load_eval_set(TEST_SET_PATH)}
