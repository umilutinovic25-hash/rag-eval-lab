# Week 7 RAG checkpoint

A small local question-answering tool over a fictional employee handbook. It retrieves chunks, answers with chunk citations and refuses questions the handbook does not cover. It runs offline: no API keys, no network, no paid services.

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

Without Ollama the CLI prints an error and exits with code 2. Set `RETRIEVAL_MODE = "lexical"` in `src/config.py` to go back to the fully offline lexical retriever. Tests always run in lexical mode and never call Ollama (`tests/conftest.py`).

## Max level: holdout, test set, LLM judge and LLM answers

Specs: `docs/maxlvl-specs.md`. Evidence: `evidence/maxlvl/`. Report: section 13.

```bash
python -m src.holdout_runner --out results/holdout.json                          # 34 holdout questions
python -m src.holdout_runner --set eval/test_set.json --out results/test.json   # 24 blind test questions
python -m src.answer_quality --set holdout --out results/answers.json           # answer text quality
```

The shipped configuration adds two steps on top of semantic retrieval:

- `RERANK = "llm-gray-zone"`: when the top cosine is between 0.50 and 0.70, `gemma3:4b` judges each of the top 5 candidates ("does the passage contain the answer?") and the system refuses if none passes. Above 0.70 it answers, below 0.50 it refuses.
- `ANSWER_MODE = "llm"`: `gemma3:4b` writes a one- or two-sentence answer from the cited chunks only, with `[chunk-id]` markers. Citations do not change.

Model replies are cached in `data/llm_cache.json`, so all three sets run offline. New questions need `ollama pull gemma3:4b`. Results: eval 12/12, holdout 33/34, blind test 22/24 (21/24 before these steps). Hybrid retrieval (`RETRIEVAL_MODE = "hybrid"`) is available but made results worse.

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
