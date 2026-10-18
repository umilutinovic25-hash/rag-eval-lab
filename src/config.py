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

# Reranking: None, "llm" (a local model judges each candidate; replaces the score thresholds above)
# or "llm-gray-zone" (the model judges only when the top score is inside RERANK_GRAY_ZONE)
RERANK = "llm-gray-zone"
RERANK_MODEL = "qwen2.5:7b"
RERANK_CANDIDATES = 5
RERANK_GRAY_ZONE = (0.50, 0.70)  # cosine scale, used only in "llm-gray-zone"
RERANK_JUDGE = "either"  # "yesno" (model answers yes/no), "span" (model copies the answering words, code checks them)
# or "either" (span with RERANK_MODEL, then yes/no with RERANK_YESNO_MODEL if span says no)
RERANK_YESNO_MODEL = "gemma3:4b"  # used only in "either"
RERANK_SPAN_PROMPT = (
    "Copy the exact words from the passage that answer the question. "
    "If the passage does not contain the answer, reply NONE.\n\n"
    "Passage: {passage}\nQuestion: {question}\nWords from the passage:"
)
RERANK_PROMPT = (
    "Question: {question}\n"
    "Passage: {passage}\n"
    "Does the passage contain the information needed to answer the question? Answer only yes or no."
)

# Answer text: "extractive" (cited chunks joined) or "llm" (a local model writes the answer from the cited chunks)
ANSWER_MODE = "llm"
ANSWER_QUOTES = False  # in "llm" mode, add the verbatim text of every cited chunk under the answer
GENERATION_MODEL = "qwen2.5:7b"
GENERATION_PROMPT = (
    "Answer the question using only facts stated in the passages below. Do not add conditions, people, steps or details "
    "that the passages do not state. Reply in one or two short sentences, then list the ids of the passages you used "
    "in square brackets, for example [hb-01-chunk-0].\n\n"
    "Passages:\n{passages}\n\nQuestion: {question}\nAnswer:"
)


def snapshot() -> dict:
    """Return the current configuration as a plain dict."""
    return {
        name: value
        for name, value in globals().items()
        if name.isupper()
    }
