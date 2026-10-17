"""All tunable parameters of the RAG pipeline.

The eval runner records every value in this module in its JSON output.
"""

# Chunking
CHUNK_STRATEGY = "sentences"  # "chars" or "sentences"
CHUNK_SIZE = 140
CHUNK_OVERLAP = 30

# Retrieval
RETRIEVAL_MODE = "semantic"  # "lexical", "semantic" or "hybrid"
EMBEDDING_MODEL = "bge-m3"  # local Ollama model, used in "semantic" and "hybrid" mode
TOP_K = 2
RETRIEVAL_MIN_SCORE = 0.01
STOPWORDS_ENABLED = False
CURRENT_ONLY = True

# Answering
REFUSAL_THRESHOLD = 0.12
SEMANTIC_REFUSAL_THRESHOLD = 0.60  # cosine scale, used in "semantic" and "hybrid" mode
CITATION_MIN_SCORE = None  # None or a float score, used only in "lexical" mode
SEMANTIC_CITATION_MIN_SCORE = 0.65  # cosine scale, used in "semantic" and "hybrid" mode


def snapshot() -> dict:
    """Return the current configuration as a plain dict."""
    return {
        name: value
        for name, value in globals().items()
        if name.isupper()
    }
