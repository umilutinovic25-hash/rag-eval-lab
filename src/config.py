"""All tunable parameters of the RAG pipeline.

The eval runner records every value in this module in its JSON output.
"""

# Chunking
CHUNK_STRATEGY = "sentences"  # "chars" or "sentences"
CHUNK_SIZE = 140
CHUNK_OVERLAP = 30

# Retrieval
RETRIEVAL_MODE = "semantic"  # "lexical", "semantic", "hybrid" (RRF), "hybrid-bm25" (weighted BM25 + cosine) or "bm25" (metrics only)
COSINE_MODES = ("semantic", "hybrid", "hybrid-bm25")  # modes whose reported score is a cosine
CHUNK_HEADERS = True  # embed "<document title>: <chunk text>"; the cited text is unchanged
BM25_K1 = 1.5
BM25_B = 0.75
HYBRID_WEIGHT = 0.5  # share of the min-max normalised cosine in "hybrid-bm25"; the rest is BM25
EMBEDDING_MODEL = "bge-m3"  # local Ollama model, used in "semantic" and "hybrid" mode
TOP_K = 2
CONTEXT_NEIGHBORS = 1  # optional expansion after selection, within the same document/version/status
CONTEXT_POLICY = "references"  # "all" or "references" (previous context only for explicit anaphora)
RETRIEVAL_MIN_SCORE = 0.01
STOPWORDS_ENABLED = False
CURRENT_ONLY = True

# Answering
EVIDENCE_RULES_ENABLED = True
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

RERANK_STRUCTURED_PROMPT = (
    "You check whether an employee handbook passage can answer a question. "
    "Return ONLY a JSON object with exactly two keys: status and evidence. "
    "status is supported if the passage provides the requested fact, contradicted if it directly rules out "
    "the premise or proposed action in the question, or insufficient if it only shares the topic. "
    "Both supported and contradicted mean that an answer can be given; a negative answer is not missing evidence. "
    "For a partial answer to a multipart question, include the fact this passage supplies. "
    "evidence is a list of complete sentences copied verbatim from the passage, or [] for insufficient. "
    "Do not infer missing facts or return yes/no.\n\n"
    "Passage: {passage}\nQuestion: {question}\nJSON:"
)


RERANK_FEWSHOT_MODEL = "gemma3:4b"  # used only in "fewshot"; a different family than GENERATION_MODEL
RERANK_FEWSHOT_PROMPT = (
    "You check whether an employee handbook passage can answer a question. The passage answers the question when it "
    "states the fact that was asked for, also when that fact is a rule that forbids, denies or limits something: a "
    "'no' answer is still an answer. The passage does not answer the question when it only mentions the same topic. "
    "Reply with yes or no only.\n\n"
    "Question: Can contractors use the staff kitchen?\nPassage: Contractors must not use the staff kitchen.\nAnswer: yes\n\n"
    "Question: How many days of paternity leave are given?\nPassage: Parental leave follows a separate policy.\nAnswer: no\n\n"
    "Question: Is the gym open on Sunday?\nPassage: The gym is open Monday to Saturday.\nAnswer: yes\n\n"
    "Question: Where do I hand in expense reports?\nPassage: Lockers are assigned by facilities.\nAnswer: no\n\n"
    "Question: {question}\nPassage: {passage}\nAnswer:"
)

# Optional second chance for yes/no-form questions: the passage may imply the answer without stating it ("3 days a week"
# answers "is the 2 day limit still in force?"). The model answers yes, no or unknown from the passage alone;
# yes and no accept the passage. None disables it; "answerability" adds it after RERANK_JUDGE rejects, and
# "answerability-only" uses it instead of RERANK_JUDGE for those questions.
YESNO_QUESTION_JUDGE = "answerability-only"  # None, "answerability" or "answerability-only"
YESNO_QUESTION_MODEL = "gemma3:4b"
YESNO_QUESTION_PROMPT = (
    "Read the passage and answer the question using only the passage. Reply with exactly one word: yes, no or "
    "unknown. Reply unknown when the passage does not say enough to decide the question.\n\n"
    "Passage: {passage}\nQuestion: {question}\nAnswer:"
)

# Answer text: "extractive" (cited chunks joined) or "llm" (a local model writes the answer from the cited chunks)
ANSWER_MODE = "llm"
ANSWER_FORMAT = "text"  # "text" (free text with [id] markers) or "json" (validated JSON rendered into the same text)
ANSWER_QUOTES = True  # in "llm" mode, add the verbatim text of every cited chunk under the answer
GENERATION_MODEL = "qwen2.5:7b"
GENERATION_PROMPT = (
    "Answer the question using only facts stated in the passages below. Do not add conditions, people, steps or details "
    "that the passages do not state. Reply in one or two short sentences, then list the ids of the passages you used "
    "in square brackets, for example [hb-01-chunk-0].\n\n"
    "Passages:\n{passages}\n\nQuestion: {question}\nAnswer:"
)
GENERATION_JSON_PROMPT = (
    "Answer the question using only facts stated in the passages below. Do not add conditions, people, steps or details "
    "that the passages do not state. Reply with ONLY a JSON object with two keys: answer (one or two short sentences) "
    "and sources (the ids of the passages you used, for example [\"hb-01-chunk-0\"]).\n\n"
    "Passages:\n{passages}\n\nQuestion: {question}\nJSON:"
)


def apply_profile(name: str) -> None:
    """CLI-only profile: change all coupled settings together, within this process."""
    global RETRIEVAL_MODE, RERANK, ANSWER_MODE, ANSWER_QUOTES, EVIDENCE_RULES_ENABLED, CHUNK_HEADERS
    if name in ("current", "verified"):
        return
    if name == "baseline":
        EVIDENCE_RULES_ENABLED = False
        CHUNK_HEADERS = False  # the historical replay keys embeddings by the bare chunk text
        return
    if name != "offline":
        raise ValueError(f"Unknown profile: {name}")
    RETRIEVAL_MODE = "lexical"
    RERANK = None
    ANSWER_MODE = "extractive"
    ANSWER_QUOTES = False


def snapshot() -> dict:
    """Return the current configuration as a plain dict."""
    return {
        name: value
        for name, value in globals().items()
        if name.isupper()
    }
