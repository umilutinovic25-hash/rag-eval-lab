"""Reproduce audit findings without Ollama or changing pipeline settings on disk.

Run from the repository root: python evidence/audit-2026-10-18/probe.py
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src import config, llm, rag, retrieval
from src.answer_quality import score_answer
from src.chunking import Chunk
from src.embeddings import cosine
from src.eval_runner import evaluate_item, run_eval
from src.holdout_runner import HOLDOUT_SET_PATH, TEST_SET_PATH, TEST2_SET_PATH, run_holdout


def emit(label, value):
    print(label, json.dumps(value, ensure_ascii=False))


passage = "Each employee has a training budget of 800 EUR per year for courses, conferences and certifications."
emit("SPAN_CHANGED_AMOUNT_ACCEPTED", llm.span_is_in_passage(passage.replace("800", "900"), passage))
emit(
    "SPAN_REMOVED_NEGATION_ACCEPTED",
    llm.span_is_in_passage(
        "Share passwords with colleagues from IT.",
        "Never share passwords, also not with colleagues from IT.",
    ),
)

answer = "Passwords do not need to be changed every 90 days [hb-05-chunk-0]."
chunk = Chunk("hb-05-chunk-0", "hb-05", "Passwords", "2026", "current", "Passwords must be changed every 90 days.")
emit(
    "CONTRADICTORY_ANSWER_QUALITY",
    score_answer(answer, [chunk.chunk_id], "every 90 days", [chunk.text, "Do passwords need to be changed?"]),
)
result = rag.RagAnswer(answer, [chunk.chunk_id], False, [retrieval.RetrievalResult(chunk, 0.9)])
item = {
    "id": "audit", "category": "supported", "expected_behaviour": "answer",
    "expected_doc_ids": ["hb-05"], "expected_fact": "every 90 days",
}
emit("CONTRADICTORY_ANSWER_EVAL_PASS", evaluate_item(item, result, {chunk.chunk_id: chunk})["pass"])
emit("MISMATCHED_VECTOR_DIMENSIONS_COSINE", cosine([1.0, 0.0], [1.0]))

with patch.object(config, "RETRIEVAL_MODE", "lexical"), patch.object(
    rag, "passage_answers", side_effect=RuntimeError("LLM judge requested")
):
    try:
        rag.build_grounded_answer("Passwords must be changed", [chunk])
    except RuntimeError as error:
        emit("LEXICAL_SWITCH_STILL_CALLS_JUDGE", str(error))

with patch.object(rag, "retrieve_top_k", return_value=[retrieval.RetrievalResult(chunk, 0.9)]), patch.object(
    rag, "write_answer", return_value="Use an invented policy [hb-99-chunk-0]."
):
    emit("UNVALIDATED_GENERATED_MARKER_SHOWN", rag.build_grounded_answer("passwords", [chunk]).answer.splitlines()[0])

for name, path in [("eval", None), ("holdout", HOLDOUT_SET_PATH), ("test1", TEST_SET_PATH), ("test2", TEST2_SET_PATH)]:
    run = run_eval() if path is None else run_holdout(path)
    emit(name, {"summary": run["summary"], "failed": [row["id"] for row in run["results"] if not row["pass"]]})
