import pytest

from src.chunking import build_chunks, split_text_with_overlap
from src.corpus import load_corpus


def test_split_text_with_overlap_returns_multiple_chunks() -> None:
    text = "abcdefghijklmnopqrstuvwxyz" * 4
    chunks = split_text_with_overlap(text, chunk_size=30, overlap=10)
    assert len(chunks) >= 3


def test_split_text_with_overlap_rejects_invalid_overlap() -> None:
    with pytest.raises(ValueError):
        split_text_with_overlap("abc", chunk_size=10, overlap=10)


def test_build_chunks_uses_stable_ids_and_keeps_metadata() -> None:
    chunks = build_chunks(load_corpus())
    ids = [chunk.chunk_id for chunk in chunks]
    assert len(ids) == len(set(ids))
    first = chunks[0]
    assert first.chunk_id == f"{first.doc_id}-chunk-0"
    assert first.version and first.status in {"current", "superseded"}
