from src.chunking import Chunk
from src.eval_runner import evaluate_item, summarise
from src.rag import REFUSAL_MESSAGE, RagAnswer

CHUNKS = {
    "doc-a-chunk-0": Chunk("doc-a-chunk-0", "doc-a", "A", "2026", "current", "Answer is 42 units."),
    "doc-b-chunk-0": Chunk("doc-b-chunk-0", "doc-b", "B", "2026", "current", "Unrelated text."),
}
SUPPORTED = {
    "id": "X1", "category": "supported", "question": "q", "expected_behaviour": "answer",
    "expected_doc_ids": ["doc-a"], "expected_fact": "42 units",
}
UNSUPPORTED = {
    "id": "X2", "category": "unsupported", "question": "q", "expected_behaviour": "refuse",
    "expected_doc_ids": [], "expected_fact": None,
}


def answer(citations: list[str]) -> RagAnswer:
    return RagAnswer(answer="...", citations=citations, refused=False, retrieved=[])


def test_padded_citations_lower_precision_but_still_pass() -> None:
    row = evaluate_item(SUPPORTED, answer(["doc-a-chunk-0", "doc-b-chunk-0"]), CHUNKS)
    assert row["fact_in_citations"] is True
    assert row["citation_precision"] == 0.5
    assert row["pass"] is True


def test_missing_fact_fails() -> None:
    row = evaluate_item(SUPPORTED, answer(["doc-b-chunk-0"]), CHUNKS)
    assert row["fact_in_citations"] is False
    assert row["citation_precision"] == 0.0
    assert row["pass"] is False


def test_correct_refusal_passes_and_answering_fails() -> None:
    refused = RagAnswer(answer=REFUSAL_MESSAGE, citations=[], refused=True, retrieved=[])
    assert evaluate_item(UNSUPPORTED, refused, CHUNKS)["pass"] is True
    wrong = evaluate_item(UNSUPPORTED, answer(["doc-a-chunk-0"]), CHUNKS)
    assert wrong["pass"] is False
    assert wrong["citation_precision"] == 0.0


def test_summary_counts_passes() -> None:
    rows = [
        evaluate_item(SUPPORTED, answer(["doc-a-chunk-0"]), CHUNKS),
        evaluate_item(UNSUPPORTED, answer(["doc-a-chunk-0"]), CHUNKS),
    ]
    summary = summarise(rows)
    assert summary["passed"] == 1
    assert summary["behaviour_accuracy"] == 0.5
