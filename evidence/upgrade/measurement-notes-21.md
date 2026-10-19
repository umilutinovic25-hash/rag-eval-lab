# Measurement notes

- All new questions and automatic expected fields were written by the same assistant that proposed the code. They are not human labels or an independent human assessment.
- Question files were frozen at bdca5d8; the exact duplicate audit passed. Textually different paraphrases of the same tiny corpus are not independent facts.
- Candidate behavior/prompts were locked at 126af44 before inspecting challenge outcomes. Baseline runs initially imported the pre-change modules. Baseline completion and code implementation overlapped in wall time; the strict D sequence “finish baseline, then implement” was not followed literally. No candidate prompt was revised from inject3 results. Default protection is strengthened only if the fixed candidate passes acceptance.
- Initial parallel runs were stopped for excessive model switching; the resumed warm baseline retains its own partial scratch entries. Completed measurements use the model-grouped driver preserved here. Cold runs use separate empty JSON caches and recompute embeddings and judges in each repeat; unused candidate requests may also be computed.
- Per-set candidate_runner seconds exclude priming and are not cold end-to-end latency. No latency improvement is claimed.
- A pass checks behavior, expected fact in cited text and citation precision, not full semantic correctness of the generated answer. The relevance judge uses the generator model family and is fallible.
- All code selection compares unchanged, predeclared switches. Any rejected behavior remains disabled; further prompt changes would need another newly committed blind set.
