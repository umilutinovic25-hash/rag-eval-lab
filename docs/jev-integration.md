# Optional JEv evidence judge

JEv is an external, paid TypeSafe API, not an Ollama model. It receives the question and selected passage text plus document metadata. Qwen remains the answer generator; local embeddings and existing injection guards stay in place. The isolated mandatory M5 package is unchanged.

## Enable explicitly

Set `TYPESAFE_API_KEY` in the server environment, or put `TYPESAFE_API_KEY=...` in the private `.env.jev` at the repository root. This file is ignored by Git; keep permissions 0600. Never paste keys into reports or chat. Environment takes priority. The file is parsed as data; shell expressions are not executed. The key is never included in config snapshots, provider state, cache keys, traces, browser responses or sanitized errors.

```sh
source .venv/bin/activate
python -m src.cli --jev --scratch results/scratch-jev-cli --question "What is the current remote work allowance?" --show-retrieved
python -m src.web --jev
```

`python -m src.web` still uses accepted local defaults. With `--jev`, current/verified profiles use the external judge; baseline and offline force it off. Existing web filters apply before evidence is sent. The adapter itself does not establish whether arbitrary user documents are authorized to leave the machine; enable it only for content you intend to send.

## Stable application contract

`src.jev.classify(question, chunks)` returns an ordered `EvidenceDecision` for each chunk: label, chosen probability, confidence, exact model ID, cached flag. `supported` and `contradicted` at probability >= 0.80 permit an answer; `insufficient` or lower probability refuses. Contradiction means evidence supports a negative answer. It is not a semantic correctness guarantee.

The adapter maps this contract to one Choice question per passage in one HTTPS request. It uses pinned `jev-1.13.0`, requires the same version in responses, validates labels, finite probabilities and their sum, the chosen maximum, confidence and token usage. Cached responses undergo the same validation. Threshold and prompt are fixed in the pre-result protocol. `confidence` is a distribution statistic, not a guarantee of correctness.

JEv checks all retrieved candidates (up to RERANK_CANDIDATES) independently of the local gray zone, replaces local candidate judges, and also validates evidence-rule shortcuts and any expanded cited context. Local injection guards run first. Existing grounding/polarity checks still apply to generated text. Uncertain or insufficient evidence produces `jev_insufficient_evidence`; missing credentials, transport, schema or cache failures produce `jev_unavailable`, with a sanitized code in the trace. No silent fallback to a different judge.

## Resilience and cache boundary

Exactly one HTTP attempt, no SDK or automatic retry. Timeout <= JEV_TIMEOUT_SECONDS (default 15 seconds), also bounded by the current operation deadline. Cancellation is checked before/after I/O; in-flight urllib I/O ends at its timeout. Redirects are refused. Input is bounded to 128 KB; response to 1 MiB. Errors are classified as missing_key, credentials_unreadable, authentication, rate_limit, timeout, unavailable, invalid_response, model_mismatch, cache_error or invalid configuration/input. Raw provider errors are never logged.

A separate `jev_cache.json` in the selected scratch directory stores only validated normalized response fields, not the key or raw error bodies. Cache identity includes full question/passage/metadata, prompt, choice rubric and pinned model. No unaccepted Jev entry goes to data/*.json. Web calls use the isolated runtime cache under the existing pipeline lock. Usage has a separate jev request/cache counter and includes provider-reported token totals. No cost estimate is inferred without reported usage.

## Frozen evaluation

40 questions in `eval/jev_set.json`, frozen in 7d97e9f before code or results; labels are AI-written from corpus2. No existing questions, metric formulas, eval_runner or eval_compare are changed. The candidate is `jev` in candidate_runner, changing only JEV_ENABLED. Evaluate all 15 sets against shipped using scratch caches. For repeatability, run the new set twice with empty caches and compare pass + ordered citations. Fake tests establish mechanics only. Live quality, latency and availability require actual API calls. Keep the feature disabled by default unless blind results and regression checks support acceptance.

References (checked 2026-10-19):
- https://docs.typesafe.ai/api
- https://docs.typesafe.ai/models (stable alias points to 1.13; preview points to 1.14)
- https://docs.typesafe.ai/confidence
- https://docs.typesafe.ai/cookbooks/classifying_rag_passages
