# G1–G8: measurement-first RAG upgrade

Baseline: commit 5cf4857 (shipped configuration unchanged until a candidate is accepted). Sources: skills `eval-harness-first`, `llm-evaluation`, `hybrid-search-implementation`, `embedding-strategies`, `vector-index-tuning`, `prompt-engineering-patterns`.

Not done on purpose: vector database, HNSW, quantization. The corpus has 10 documents / 26 chunks; flat search is correct below 10K vectors.

| ID | Deliverable | Acceptance |
| --- | --- | --- |
| G1 | Retrieval metrics (`src/retrieval_metrics.py`): Recall@k, MRR, nDCG@k at document and fact level, per category, for all sets | Offline, no LLM. Baseline numbers saved before any variant is tried. |
| G2 | Test set 3 (`eval/test3_set.json`, 36 questions, dimension-based: fact type × yes/no polarity × multipart × versioned × near-domain refusal) | Committed before any experiment (e81d65f). Run once for the baseline and once for the final configuration. Assistant-authored, not human-labelled; the corpus has ~35 facts, so independence from sets 1–4 is limited. |
| G3 | Judge calibration (`src/judge_calibration.py`): TPR/TNR of each judge on labelled (question, passage) pairs from all sets; candidates from a different model family than the generator (`qwen2.5:7b`) | Labels come from `expected_fact` appearing in the passage, a heuristic, and the sets are seen sets. Results are advisory. |
| G4 | Contextual chunk headers (`CHUNK_HEADERS`): document title prepended to the text that is embedded, never to the cited text | Accepted only if retrieval metrics do not fall and no seen-set pass count drops. |
| G5 | BM25 with IDF and weighted fusion (`RETRIEVAL_MODE = "hybrid-bm25"`) to retest hybrid fairly | Same rule as G4. The reported score stays cosine, so thresholds keep their meaning. |
| G6 | `TOP_K` sweep 1–5 | Same rule; evidence is the metric table. |
| G7 | Few-shot judge (`RERANK_JUDGE = "fewshot"`) with negative-answer examples for yes/no questions | Same rule plus calibration TPR/TNR not worse than `either`. |
| G8 | Structured JSON answers (`ANSWER_FORMAT = "json"`), rendered into the existing `[chunk-id]` text and still passed through `generation_issue` | Same rule plus fallback count not higher. |

Acceptance rule for any candidate: on eval, holdout, test and test2 the pass count must not fall and mean citation precision must not fall, and at least one stated metric must improve. Otherwise the option stays implemented and disabled, as with hybrid RRF and the structured judge before. A candidate is then run once on test 3 together with the baseline. Test 3 is not used to choose between candidates.

Experiments use a scratch copy of the caches (`results/scratch/`); committed caches only grow after a candidate is accepted. Original eval sets, metric code, corpus and the M5 minimum stay unchanged.
