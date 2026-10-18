# Week 7 RAG checkpoint

A small local question-answering tool over a fictional employee handbook. It retrieves chunks, answers with chunk citations and refuses questions the handbook does not cover. The mandatory M5 checkpoint runs offline. The advanced HEAD uses local models for uncached questions; cached replay needs no model server. No API keys or paid services are used.

This week you will **measure** this system on a fixed eval set, find failures, apply **exactly one** improvement and compare results before and after.

## Setup

Python 3.12.

```bash
python3 -m venv .venv
. .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest              # or ./scripts/run_tests.sh
```

All tests pass on the starting state. Tests check mechanics, not quality; quality is measured by the eval runner.

## Commands

| Command | What it does |
| --- | --- |
| `python -m src.cli --question "How often do passwords need to be changed?"` | Answer or refusal with citations (title, version, status) |
| `python -m src.cli --question "..." --show-retrieved` | Also prints retrieved chunks with their scores |
| `python -m src.eval_runner --out results/before.json` | Runs all 12 questions, prints the table and summary, saves the run |
| `python -m src.eval_compare results/before.json results/after.json` | Fixed, regressed and unchanged questions, metric deltas, changed settings |

## Semantic retrieval (advanced part)

The current configuration uses `RETRIEVAL_MODE = "semantic"`: chunks are ranked by cosine similarity of local `bge-m3` embeddings served by [Ollama](https://ollama.com). Embeddings are cached in `data/embedding_cache.json` (committed), so the eval runner and the CLI for the 12 eval questions run offline without Ollama.

A question that is not in the cache needs Ollama:

```bash
ollama pull bge-m3
ollama serve
```

Without Ollama the CLI prints an error and exits with code 2. For a fully model-free CLI use `python -m src.cli --profile offline --question "..."`. This sets lexical retrieval, disables reranking, and selects extractive answers together. Changing only RETRIEVAL_MODE is insufficient. Tests always run in lexical mode and never call Ollama (`tests/conftest.py`).

## Max level: holdout, test set, LLM judge and LLM answers

Specs: `docs/maxlvl-specs.md`. Evidence: `evidence/maxlvl/`. Report: section 13.

```bash
python -m src.holdout_runner --out results/holdout.json                          # 34 holdout questions
python -m src.holdout_runner --set eval/test_set.json --out results/test.json   # test set 1 (24, blind for round 1)
python -m src.holdout_runner --set eval/test2_set.json --out results/test2.json # test set 2 (32, blind for round 2)
python -m src.answer_quality --set holdout --out results/answers.json           # answer text quality
```

The shipped configuration adds two steps on top of semantic retrieval:

- `RERANK = "llm-gray-zone"`: when the top cosine is between 0.50 and 0.70, each of the top 5 candidates is judged and the system refuses if none passes. Above 0.70 it answers, below 0.50 it refuses. With `RERANK_JUDGE = "either"` a passage passes if `qwen2.5:7b` copies answering words that are verified to come from the passage, or if `gemma3:4b` says yes.
- `ANSWER_MODE = "llm"`: `qwen2.5:7b` writes a short answer from the cited chunks only, with `[chunk-id]` markers. With `ANSWER_QUOTES = True` the verbatim text of every cited chunk follows as `Source [id]: "..."`. Citations do not change.

Model replies are cached in `data/llm_cache.json`, so all four sets run offline. New questions need `ollama pull qwen2.5:7b` and `ollama pull gemma3:4b`. Results: eval 12/12, holdout 34/34, test 1 23/24, test 2 29/32 (blind; 28/32 before round 2). Hybrid retrieval (`RETRIEVAL_MODE = "hybrid"`) is available but made results worse.

## Project layout

- `src/config.py`: every tunable setting in one place. The eval runner saves all values with each run.
- `src/corpus.py`: ten handbook documents with title, section, version and status.
- `src/chunking.py`, `src/retrieval.py`, `src/rag.py`: the pipeline.
- `src/embeddings.py`: Ollama embeddings with an on-disk cache (semantic mode only).
- `src/eval_runner.py`, `src/eval_compare.py`: evaluation and comparison.
- `eval/eval_set.json`: the fixed eval set.
- `docs/improvement-menu.md`: one-change options.

## Metrics

| Column | Meaning |
| --- | --- |
| `Hit` | For questions that should be answered: at least one retrieved chunk comes from an expected document |
| `Fact` | The expected fact appears in at least one cited chunk |
| `CitPrec` | Cited chunks from expected documents divided by all cited chunks (0.00 when answering a question that should be refused) |
| `Pass` | Correct behaviour (answer or refuse) and, for answered questions, the fact is cited and `CitPrec` is at least 0.50 |

## Rules for this week

1. **Do not edit `eval/eval_set.json`.** Every run prints its SHA-256; runs with different hashes cannot be compared.
2. Run the baseline first: `python -m src.eval_runner --out results/before.json`.
3. Change one thing (see `docs/improvement-menu.md`), then run the same command with `--out results/after.json`.
4. Compare with `eval_compare` and put both runs and the comparison output in your report.

Result files in `results/` are ignored by git. Copy the printed tables into your report.

## Reliability fixes and reproducibility (C1–C6)

Copied evidence now must be a contiguous token span from a source sentence and must preserve its negation. This checks transcription, not whether the passage answers the question. LLM answers with empty text, unknown/unbalanced citation markers, generated Source lines, or numeric values absent from the cited text fall back to extractive output. The fallback reason is exposed on RagAnswer. These checks do not prove semantic correctness.

```bash
python -m src.cli --profile offline --question "What is the annual leave allowance?"
python -m src.answer_quality --set test2 --out results/quality-test2.json
python -m src.experiment_runner --mode replay --out results/replay.json
```

The replay runner forbids all model requests and records source, corpus, question-set and cache hashes, settings, timings and call counts. Semantic correctness stays `not_assessed` in answer-quality output; lexical risk flags require review. Refusals remain in the report denominator. All existing question sets are now seen sets; replays are not fresh blind tests.

Optional fresh measurement: `python -m src.experiment_runner --mode cold --out results/cold.json`. This requires already installed models and a running Ollama, uses isolated temporary caches, and records observed local model digests/version. It does not download models or replace committed caches. Cold mode has not been run for C1–C6. Historical cache model digests are unknown; current model identity cannot establish their provenance.

See `docs/hardening-spec.md`, report section 14 and `evidence/hardening/`. The original eval and metrics code remain unchanged. `python scripts/package_minimum.py` builds a separate M5 submission archive from checkpoint 45b8172 plus its evidence; fill the human review/contribution fields before submission.

## D1–D6: evidence context, traces, and completion reliability

The retained configuration uses `CONTEXT_NEIGHBORS = 1`, `CONTEXT_POLICY = "references"`: an explicit "same/that/this form/policy/procedure/process" reference receives preceding context from the same document/version/status. Ordinary candidates are not expanded. H20 now identifies IT portal / Hardware. Expanding all neighbors was tested and rejected because H14 citation precision regressed.

Judge filtering stops after TOP_K accepted candidates. Completion metadata is saved alongside the text cache in `data/llm_cache-metadata.json`; historical entries have unknown completion reasons. Truncated generation uses extractive output. Experiments persist full answers, traces, request successes/failures, fallback counts, and actual cold-cache snapshots instead of deleting the only raw evidence.

Quantity/unit and action-negation guards catch the tested "90 years" / "90 days" and direct obligation reversals, but are conservative lexical heuristics. The optional `structured` judge with JSON support/contradiction status was tested, including strict parsing of an optional JSON fence; it regressed other questions and remains disabled. The shipped judge is still `either`.

```bash
python -m src.completeness --out results/completeness.json
python -m src.experiment_runner --mode replay --out results/replay-with-traces.json
```

`review/completeness-rubric.json` is explicitly an assistant draft, not a human-approved reference or semantic grader. See `docs/improvements-spec.md`, `docs/improvements-results.md`, `evidence/improvements/`. A real empty-cache smoke test for H20 succeeded (1 embedding + 10 LLM requests, no errors/fallback); this is not a fresh generalization test or a cold run of all 102 questions.
