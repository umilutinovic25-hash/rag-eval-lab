# G1–G8: results

Spec: `docs/rag-upgrade-spec.md`. Raw data: `evidence/upgrade/`. Commands are at the end. All numbers below were produced by the scripts, not by hand. Nothing here is a human-reviewed reference.

## Corrections to the previous analysis

- The four yes/no failures listed before (T02, U07, U11, U13) were already fixed by the F1 evidence rules; the shipped replay is 12/12, 34/34, 24/24, 32/32 (102/102). They are not an open problem on the seen sets.
- The open problem is on unseen questions: see test 3 below.

## G1 Retrieval metrics (72 answerable questions, seen sets, no LLM)

| Variant | MRR | nDCG@5 | Fact recall@1 | @2 | @3 | @5 |
| --- | --- | --- | --- | --- | --- | --- |
| previous (bare chunk text) | 0.972 | 0.980 | 0.944 | 1.000 | 1.000 | 1.000 |
| **headers (shipped)** | **1.000** | **1.000** | **1.000** | 1.000 | 1.000 | 1.000 |
| BM25 only | 0.808 | 0.827 | 0.722 | 0.847 | 0.875 | 0.903 |
| hybrid BM25, weight 0.3 / 0.5 / 0.7 | 0.850 / 0.894 / 0.949 | 0.870 / 0.916 / 0.962 | 0.764 / 0.819 / 0.903 | 0.903 / 0.931 / 0.986 | | |
| headers + hybrid BM25 0.5 | 0.912 | 0.930 | 0.847 | 0.958 | 0.972 | 0.986 |
| hybrid RRF (earlier) | 0.821 | 0.842 | 0.722 | 0.861 | 0.889 | 0.931 |

Retrieval was never the bottleneck: the expected fact is in the top 2 for every answerable seen question. A fair BM25 (IDF, length normalisation) does not rescue hybrid search: every fused variant is worse than semantic alone, so the earlier "hybrid hurts" finding stands with a stronger lexical scorer.

## G4 Contextual chunk headers: accepted

`CHUNK_HEADERS = True` embeds `"<title>: <text>"`; cited text is unchanged. Pipeline on the seen sets: 12/12, 34/34, 24/24, 32/32, identical citation precision (1.00, 0.958, 1.00, 1.00), same fallback counts. Recall@1 0.944 → 1.000. Cosines move (highest top cosine among questions that must be refused 0.676 → 0.625, lowest among answerable ones 0.540 → 0.528, more answerable questions inside the 0.50–0.70 gray zone: 33 → 39 of 72), but no decision crossed a threshold. The `baseline` web profile keeps bare text so its legacy replay is unchanged. Committed caches only gained keys (embeddings 126 → 186, LLM 1063 → 1406).

## G6 TOP_K: unchanged (2)

| TOP_K | eval | holdout | test | test2 |
| --- | --- | --- | --- | --- |
| 1 | 12/12 | 34/34, cit 1.00 | 24/24 | 32/32 |
| **2** | 12/12 | 34/34, cit 0.958 | 24/24 | 32/32 |
| 3 | 12/12 | **33/34** (H09) | 24/24 | 32/32 |

TOP_K=1 scores marginally higher citation precision on one holdout question, but the completeness rubric covers only 4 questions, so there is no evidence it is safe for multipart questions. TOP_K=3 regresses. Kept at 2.

## G3 Judge calibration

510 pairs (top-5 candidates of 102 seen questions), 72 positive. Label heuristic: expected document and expected fact in the passage. Seen data, advisory only; 95% Wilson intervals are in the JSON (TPR intervals are wide, about ±0.08–0.1).

| Judge | Family | Different from generator | TPR | TNR | Gray zone TPR / TNR |
| --- | --- | --- | --- | --- | --- |
| span qwen2.5:7b | qwen | no | 0.806 | 0.993 | 0.795 / 1.000 |
| yes/no qwen2.5:7b | qwen | no | 0.750 | 0.998 | 0.641 / 1.000 |
| yes/no gemma3:4b | gemma | yes | 0.847 | 0.954 | 0.795 / 0.967 |
| **either (shipped)** | qwen+gemma | **no** | 0.903 | 0.952 | 0.872 / 0.967 |
| few-shot gemma3:4b | gemma | yes | 0.917 | 0.811 | 0.897 / 0.813 |
| yes/no mistral | mistral | yes | 0.903 | 0.954 | 0.897 / 0.955 |
| few-shot mistral | mistral | yes | 0.944 | 0.742 | 0.923 / 0.756 |
| yes/no llama3.2 | llama | yes | 0.917 | 0.904 | 0.897 / 0.923 |
| few-shot llama3.2 | llama | yes | 0.833 | 0.705 | 0.821 / 0.703 |

- The shipped judge uses `qwen2.5:7b` in its span step, the same family as the answer generator, which `eval-harness-first` forbids for a gating judge. It therefore stays advisory evidence of quality, not a calibrated gate.
- Few-shot examples raise TPR and cut TNR sharply (many false accepts) in all three families.
- Plain yes/no mistral matches `either` on this heuristic (0.903 / 0.954) with one call instead of two and a different family.

## G7 Few-shot judge: rejected

| Candidate | eval | holdout | test | test2 |
| --- | --- | --- | --- | --- |
| few-shot gemma3:4b | 12/12 | **30/34** | **22/24** | **29/32** |

Fails H20, H24, H25, H34, T19, T21, U05, U23, U26, consistent with its TNR of 0.81. Stays implemented (`RERANK_JUDGE = "fewshot"`) and disabled.

## Different-family single judge: rejected

`RERANK_JUDGE = "yesno"`, `RERANK_MODEL = "mistral:latest"`: 12/12, **31/34** (H13, H25, H34), 24/24, 32/32. Not adopted despite the matching calibration numbers; calibration on heuristic labels does not predict end-to-end behaviour on near-domain refusals.

## G8 JSON answers: rejected

`ANSWER_FORMAT = "json"`: 102/102 and identical precision, but 3 extractive fallbacks (holdout 1, test2 2) against 2 for the shipped text format, so it fails the "fallback not higher" rule. Implemented and disabled.

## G2 Blind test 3 (36 questions, run once per configuration)

Assistant-authored, committed before any experiment (e81d65f); the corpus has about 35 facts, so it is only partly independent of sets 1–4.

| Configuration | Passed | Behaviour accuracy | Mean citation precision | Failures |
| --- | --- | --- | --- | --- |
| previous (bare text) | 33/36 | 0.917 | 0.896 | V21, V25, V30 |
| **shipped (headers)** | **34/36** | 0.944 | **0.978** | V21, V25 |

Retrieval hit rate 1.00 for both. V30 ("How often are performance reviews held?", a refusal) was answered from the onboarding check-in chunk by the old configuration and refused by the new one.

Remaining failures, both false refusals of answerable yes/no questions:

- V21 "Are parking spaces assigned to individual people permanently?" (answer: first come, first served): the right chunk is first (cosine 0.596) and the judge rejects it.
- V25 "Is the old limit of 2 remote days per week still in force?": the judge rejects hb-03-chunk-0/2.

So on unseen answerable questions the system refuses 2 of 25 (8%) that it should answer; the seen-set 102/102 overstates generalisation. These two were deliberately not used to tune anything. A further round needs a new blind set. Test 3 is now a seen set.

## What was not done and why

- No vector database, HNSW or quantization: 26 chunks.
- No cross-encoder reranker: none is installed locally and no model is downloaded automatically.
- No human labelling or approval: the calibration labels and test 3 are assistant-derived.

## Reproduce

```bash
python -m src.retrieval_metrics --out results/retrieval-metrics.json          # offline apart from new embeddings
python -m src.candidate_runner --candidates previous shipped --out results/candidates.json
python -m src.judge_calibration --out results/judge-calibration.json          # needs Ollama + gemma3, mistral, llama3.2
python -m src.holdout_runner --set eval/test3_set.json --out results/test3.json
```

All experiment commands use scratch cache copies in `results/scratch*`; the committed caches contain only the shipped configuration.

# Round 2: V21, V25 and blind test 4

Order of work: test 4 (40 questions, `eval/test4_set.json`) was committed first (d5d537d), then the fix was designed on seen data, then test 4 was run once per configuration. Test 4 is a seen set from here on.

## Diagnosis

V21 and V25 are implicit answers: "spaces are shared ... first come, first served" answers "assigned permanently?" and "up to 3 days per week" answers "is the 2 day limit still in force?" without stating it. Every judge (span, yes/no, qwen, gemma) says No to "does the passage contain the information needed", so the question is refused although the right chunk is ranked first.

## Fix: three-way answerability judge for yes/no-form questions

`YESNO_QUESTION_JUDGE`: for questions starting with an auxiliary verb, the model answers `yes`, `no` or `unknown` from the passage alone; yes and no accept the passage. Calibration on the 47 yes/no questions of the seen sets (235 pairs, 37 positive):

| Judge | TPR | TNR |
| --- | --- | --- |
| shipped `either` | 0.757 | 0.949 |
| 3-way gemma3:4b | 0.892 | 0.980 |
| 3-way qwen2.5:7b (generator family) | 0.919 | 0.985 |
| 3-way mistral | 0.703 | 0.985 |
| 3-way llama3.2 | 0.892 | 0.551 |
| either + 3-way gemma / mistral / qwen | 0.892 / 0.811 / 0.946 | 0.939 / 0.944 / 0.939 |

On the seen sets both variants fix V21 and V25 (test 3: 34/36 → 36/36) with every other set unchanged.

## Blind test 4: the first version did not generalise

| Configuration | Passed | Mean citation precision | Failures |
| --- | --- | --- | --- |
| before (no yes/no judge) | 36/40 | 0.875 | W05, W10, W26, W38 |
| 3-way gemma **replacing** the shipped judge (chosen from calibration, run once) | **34/40** | 0.920 | W05, W10, **W20, W22**, W26, W38 |
| post-hoc: 3-way gemma **after** the shipped judge (union) | 36/40 | 0.875 | W05, W10, W26, W38 |
| post-hoc: union with qwen2.5:7b | 38/40 | 0.862 | W05, W38 |

- Replacing the judge was a design error: `gemma3:4b` says `unknown` for clear passages (W20, W22) that the span judge accepts, so two correct answers were lost. Calibration on seen pairs (TPR 0.892) did not predict this.
- `gemma3:4b` also says `unknown` for the implicit cases W05 (leave does not disappear), W10 (agree before booking) and W26 (no reserved spot, the same situation as V21), so the fix is narrow: it repairs the two questions it was designed on and nothing on test 4.
- The qwen variant fixes W10 and W26 but is the generator's family and lowers citation precision, so it is not shipped. Its numbers are post-hoc on a seen set.

## Shipped

`YESNO_QUESTION_JUDGE = "answerability"` (union, `gemma3:4b`). A union can only add acceptances, never remove one the shipped judge made. Results on all six sets: 12/12, 34/34, 24/24, 32/32, **36/36**, 36/40 (identical to before on test 4, which is the post-hoc number). Refusal questions in yes/no form (H27, H28, W30–W33, W36 and others) were not newly answered. No independent blind validation of this final configuration exists; a test 5 would be needed.

Remaining known failures on unseen-style questions: W05, W10, W26 (implicit yes/no refused) and W38 ("What time does the office open in the morning?" is answered from the IT support hours). Reproduce: `python -m src.candidate_runner --sets test4 --candidates before-yesno3 shipped yesno3-only` and `python -m src.judge_calibration --yes-no-only`.
