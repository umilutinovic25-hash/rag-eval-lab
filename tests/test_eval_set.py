from src.corpus import load_corpus
from src.eval_runner import load_eval_set

CATEGORIES = {"supported", "chunk-boundary", "paraphrase", "versioned", "unsupported", "unsupported-near-domain"}


def test_eval_set_has_twelve_unique_questions() -> None:
    items = load_eval_set()
    assert len(items) == 12
    assert len({item["id"] for item in items}) == 12


def test_eval_set_fields_are_consistent() -> None:
    docs = {doc.doc_id: doc for doc in load_corpus()}
    for item in load_eval_set():
        assert item["category"] in CATEGORIES
        assert item["question"].strip()
        if item["expected_behaviour"] == "refuse":
            assert item["expected_doc_ids"] == []
            assert item["expected_fact"] is None
        else:
            assert item["expected_behaviour"] == "answer"
            assert item["expected_doc_ids"]
            texts = [docs[doc_id].text.lower() for doc_id in item["expected_doc_ids"]]
            assert any(item["expected_fact"].lower() in text for text in texts)
