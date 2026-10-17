"""All tunable parameters of the RAG pipeline.

The eval runner records every value in this module in its JSON output.
"""

# Chunking
CHUNK_STRATEGY = "sentences"  # "chars" or "sentences"
CHUNK_SIZE = 140
CHUNK_OVERLAP = 30

# Retrieval
TOP_K = 2
RETRIEVAL_MIN_SCORE = 0.01
STOPWORDS_ENABLED = False
CURRENT_ONLY = True

# Answering
REFUSAL_THRESHOLD = 0.12
CITATION_MIN_SCORE = None  # None or a float score


def snapshot() -> dict:
    """Return the current configuration as a plain dict."""
    return {
        name: value
        for name, value in globals().items()
        if name.isupper()
    }
