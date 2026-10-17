# Improvement menu

Pick **one** change, write a short change spec, apply it, and rerun the full eval set with the same command. Every option is controlled from `src/config.py`. Options marked *implement* need a small code change in the place where the setting is read; the starter raises `NotImplementedError` there until you implement it.

| ID | Change | Setting | What it changes | What to watch for |
| --- | --- | --- | --- | --- |
| M1 | Sentence-aware chunking (*implement*) | `CHUNK_STRATEGY = "sentences"` in `chunking.py` | Chunks are built from whole sentences, packed up to `CHUNK_SIZE` characters. A sentence longer than `CHUNK_SIZE` becomes its own chunk. No overlap is needed. | Chunk lengths change, so every score changes, not only the questions you target. |
| M2 | Stopword filtering (*implement*) | `STOPWORDS_ENABLED = True` in `retrieval.py` | A fixed list of about 40 common English words is removed from both query and chunk tokens before scoring. | Scores rise for chunks that share meaningful words; some questions may now match nothing. |
| M3 | Refusal threshold calibration | `REFUSAL_THRESHOLD` | The system refuses when the best retrieved score is below this value. | Too low: unsupported questions get answers. Too high: supported questions get refused. |
| M4 | Citation score threshold (*implement*) | `CITATION_MIN_SCORE` in `rag.py` | Only retrieved chunks with a score at or above this value are cited. The top result is always cited when answering. | Fewer padding citations, but a weak chunk that holds the needed fact may be dropped. |
| M5 | Current-version filter (*implement*) | `CURRENT_ONLY = True` in `retrieval.py` | Documents with status `superseded` are not searchable. | Questions about history or older rules can no longer be answered. |
| M6 | Top-k change | `TOP_K` | How many chunks are retrieved and cited. | Fewer chunks: less noise but less recall. More chunks: more recall but more padding. |

Rules:

- Do not edit `eval/eval_set.json`. Its SHA-256 is printed with every run and `eval_compare` refuses to compare runs made with different eval sets.
- One change means one intent. If you need two settings to make one idea work, explain why in the spec; `eval_compare` will warn you.
- A result that stays wrong after your change is evidence too. Write it down as a remaining limitation.
