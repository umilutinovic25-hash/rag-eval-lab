# RAG Eval Lab

Measuring and improving a deliberately weak RAG system, one controlled change at a time.

The starting point was a small question-answering tool over a fictional employee handbook that scored **6/12** on a fixed eval set: it cited outdated policies, split facts across chunk boundaries, missed paraphrases and answered questions it should have refused. Every improvement here was made the same way: write the spec and freeze the test questions first, change one thing, measure it against the previous result, and keep it only if nothing regressed.

Everything runs locally with [Ollama](https://ollama.com). No paid APIs.

## Results

| | Before | After |
| --- | ---: | ---: |
| Fixed eval set (12 questions) | 6/12 | **12/12**, citation precision 1.00 |
| All 22 question sets (508 questions, incl. blind sets run once) | | **489/508 (96.3%)** |
| Historical-version questions | 9/20 | **20/20**, blind sets 16/16 |
| Prompt-injection blind set | 6/10 | **10/10** |

Retrieval on 174 answerable questions: MRR 0.979, correct document at rank 1 in 99.4% of cases.

The 19 remaining failures are documented rather than tuned away: near-domain questions the corpus cannot answer, implicit yes/no questions and some multi-part questions. Several attempts to fix them each broke other questions, so they stay listed as limitations.

## How each change was made

1. **Diagnose** on concrete eval questions (e.g. E06: answered from the 2024 superseded policy instead of the 2026 one).
2. **Spec first.** Hypothesis, expected effect, regression risk and acceptance rule, committed before the code (`docs/*-spec.md`).
3. **Freeze new questions** before the first run. `scripts/check_sets.py` fails if a frozen set changes later.
4. **One change behind a config switch**, measured against the previous configuration with `src/eval_compare.py` (fixed, regressed, changed settings, eval-set hash).
5. **Regression audit.** For late changes, find every existing question the change can affect at all (e.g. whose candidate list differs), and measure exactly those before and after. Everything else is unchanged by construction.
6. **Keep or reject.** Rejected changes stay in the code, disabled, with the measurement that rejected them.

## What was accepted and what was rejected

| Change | Result | Decision |
| --- | --- | --- |
| Current-version filter (`CURRENT_ONLY`) | E06 fixed, 6 → 7/12 | accepted |
| Sentence-based chunking | E04, E09 fixed, 7 → 9/12 | accepted |
| Calibrated refusal threshold | E10 fixed, 9 → 10/12 | accepted |
| Semantic retrieval (`bge-m3` embeddings) | E05, E11 fixed, 10 → 12/12 | accepted |
| Citation score floor | citation precision 0.83 → 1.00 | accepted |
| LLM passage judge in the uncertain score band | holdout and blind sets improved | accepted |
| Document title in the embedded text | fact recall@1 0.944 → 1.000 | accepted |
| Version-aware retrieval for historical questions | 9/20 → 20/20, one existing question fixed, none broken | accepted |
| Injection guards v2 (false premises, hidden-text requests) | blind attack set 6/10 → 10/10, no regressions | accepted |
| Hybrid BM25/RRF retrieval | worse than semantic at every weight | rejected |
| Query rewriting | MRR 0.979 → 0.967 | rejected |
| Version context for present-tense questions | fixes 1, breaks 2 (one blind) | rejected |
| External LLM judge (JEv) | 38/40 → 38/40, different errors | optional, off |

## Cost

Measured on the 12 eval questions from empty caches (`scripts/measure_cost.py`):

| Profile | Eval | Time per question (cold) | LLM calls | Needs |
| --- | ---: | ---: | ---: | --- |
| Offline (lexical, extractive) | 10/12 | ~0 s | 0 | nothing |
| Semantic retrieval, extractive answer | 12/12 | 0.15 s | 0 | Ollama, `bge-m3` |
| Full system (judge + generated answer) | 12/12 | 4.4 s | 26 | Ollama, `bge-m3`, `qwen2.5:7b`, `gemma3:4b` |

With caches, every profile answers the full set in under 0.1 s.

## Pipeline

Question → injection guards → version-aware candidate filter → semantic retrieval (`bge-m3`, title-prefixed chunks) → LLM judge for candidates in the uncertain score band (`qwen2.5:7b` span copy, `gemma3:4b` yes/no) → answer generated from cited passages only, with `[chunk-id]` markers and verbatim source quotes → structural and numeric checks, falling back to extractive output → yes/no polarity check by a second model family.

Model replies and embeddings are cached in `data/`, so the committed eval sets replay without a model server.

## Run it

Python 3.12.

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python -m pytest                                    # 288 tests, no models needed
python -m src.eval_runner --out results/run.json    # 12/12 from cache
python -m src.cli --question "How many days per week can I work remotely?"
python -m src.cli --profile offline --question "How often must passwords be changed?"   # no models at all
```

New questions need Ollama with `bge-m3`, `qwen2.5:7b` and `gemma3:4b`.

Web workspace (React + TypeScript, Serbian UI): `./start-web.command`, then `http://localhost:8767`. It shows answers with clickable citations, decision traces, document versions and every evaluation set.

Local quality gate: `./scripts/check.sh` (tests, frozen-set hashes, paired comparison). Frontend: `npm --prefix frontend run test` and `npm --prefix frontend run test:e2e`.

## Repository map

- `src/`: pipeline (`retrieval.py`, `rag.py`, `llm.py`, `evidence.py`), evaluation (`eval_runner.py`, `eval_compare.py`, `retrieval_metrics.py`, `candidate_runner.py`) and web server.
- `eval/`: 22 frozen question sets and a second, independent corpus.
- `docs/`: one spec per change, written before the code. `docs/DEVELOPMENT.md` has the full developer notes.
- `evidence/`: saved runs, comparisons and audits behind every number above.
- `REPORT_BEFORE_AFTER.md`: the full experiment log (in Serbian), sections 1–11 for the original single change, 12–26 for everything after.
- `frontend/`: web workspace with unit and Playwright tests.

## Context

Built as the week 7 assignment of an AI engineering bootcamp, starting from a provided weak checkpoint. The mandatory part allowed exactly one change (the current-version filter, 6 → 7/12); everything after it is the optional advanced part. The handbook and stores are fictional. AI assistants helped with code and drafting; every claim here is backed by a saved measurement in `evidence/`.
