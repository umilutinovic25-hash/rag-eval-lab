import argparse
import sys
from pathlib import Path

from . import config
from .chunking import build_chunks
from .corpus import load_corpus
from .embeddings import EmbeddingError
from .llm import LLMError
from .rag import build_grounded_answer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Week 7 RAG checkpoint")
    parser.add_argument("--profile", choices=["current", "offline"], default="current", help="offline disables all model calls")
    parser.add_argument("--question", required=True, help="Question to ask over the handbook")
    parser.add_argument("--show-retrieved", action="store_true", help="Also print retrieved chunks and scores")
    parser.add_argument("--jev", action="store_true", help="Use the optional external TypeSafe judge (requires an API key)")
    parser.add_argument("--scratch", type=Path, default=Path("results/scratch-jev-cli"), help="Cache directory for --jev")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config.apply_profile(args.profile)
    if args.jev:
        from .jev import JevError, api_key
        from .scratch import use_scratch_caches
        if args.profile == "offline":
            print("Error: --jev cannot be combined with the offline profile.", file=sys.stderr)
            sys.exit(2)
        try:
            api_key()
        except JevError as error:
            print(f"Error: {error}", file=sys.stderr)
            sys.exit(2)
        config.JEV_ENABLED = True
        use_scratch_caches(args.scratch)
    chunks = build_chunks(load_corpus())
    by_id = {chunk.chunk_id: chunk for chunk in chunks}
    try:
        result = build_grounded_answer(args.question, chunks)
    except (EmbeddingError, LLMError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(2)

    print("Question:")
    print(args.question)
    print("\nAnswer:")
    print(result.answer)
    print("\nRefused:", result.refused)
    print("Citations:")
    if not result.citations:
        print("  None")
    for chunk_id in result.citations:
        chunk = by_id[chunk_id]
        print(f"  {chunk_id}: {chunk.title} (version {chunk.version}, {chunk.status})")

    if args.show_retrieved:
        print("\nRetrieved:")
        for item in result.retrieved:
            print(f"  {item.score:.4f}  {item.chunk.chunk_id}: {item.chunk.text}")


if __name__ == "__main__":
    main()
