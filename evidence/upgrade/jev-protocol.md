# JEv experiment — frozen before implementation and execution

Date: 2026-10-19. Author: AI assistant; not independent human annotation.

`eval/jev_set.json`: 40 new questions on corpus2, including supported/versioned/identifier/multipart/implicit-binary cases, 10 near-domain negatives, 5 injection requests and 5 benign controls. Expected labels come only from corpus2, without looking at execution results. Exact duplicate checking is required. Existing sets and metric code must remain unchanged.

## Predeclared candidate

Optional `JEV_ENABLED = False`. When explicitly enabled, use Jev as an independent evidence decision before generation, including evidence-rule shortcuts. In the retrieval path, Jev replaces local candidate judging and checks up to RERANK_CANDIDATES current candidates even outside the local gray zone. It receives only the question, candidate text and document metadata, never gold labels. A single Choice per candidate: supported / contradicted / insufficient. Supported and contradicted permit an answer if their selected probability is at least 0.80; explicit negative answers count as answerable. Shared topic alone does not suffice. Uncertain and insufficient do not permit an answer. No fallback to another judge on provider failure: refuse with an explicit service reason.

Use pinned `jev-1.13.0` (documented stable alias target on 2026-10-19), HTTPS API only, server environment key, bounded timeout, no automatic retries, sanitized errors. Store provider output in scratch cache only, keyed by complete request and pinned version. Validate schema and version on cache replay too. Never log the key or raw transport errors.

## Evaluation and acceptance

Commit this protocol and set before implementation. Freeze prompt and thresholds before any result is read. Compare shipped and jev on all 15 sets; final panel displays shipped, not an unaccepted candidate. New questions become seen after their first execution. Two fresh scratch repetitions must compare pass + ordered citations; report cache provenance. Do not infer live quality from fake transport tests. If no API key is available, finish integration and fake tests, record live evaluation as pending, and keep JEv disabled. No claims of improvement without blind live measurement. Do not alter the isolated mandatory M5 submission.
