"""Group identical judge requests by model to avoid local model reloads. No gold labels read.

Scratch only. This changes execution order and may compute unused candidate verdicts;
it does not change prompts, generation settings, retrieval or grading. Not a latency benchmark.
"""
import json
import re
from pathlib import Path
from src import config, llm
from src.candidate_runner import corpus_chunks
from src.embeddings import embed
from src.retrieval import chunk_embedding_text, searchable_chunks, retrieve_top_k
from src.rag import select_citations, expand_context


def prime(names, default):
    corpus = {name: corpus_chunks(name, default) for name in names}
    questions = {name: [i['question'] for i in json.loads(Path(f'eval/{name}_set.json').read_text())] for name in names}
    texts = [q for values in questions.values() for q in values]
    texts += [chunk_embedding_text(c) for chunks in corpus.values() for c in searchable_chunks(chunks)]
    embed(list(dict.fromkeys(texts)))
    jobs = []
    for name in names:
        for q in questions[name]:
            version = config.VERSION_CONTEXT and bool(re.search(r'\b(current|latest|active|superseded|still|now|in force|20\d{2})\b', q, re.I))
            candidates = retrieve_top_k(q, corpus[name], k=config.RERANK_CANDIDATES)
            top = candidates[0].score if candidates else 0
            low, high = config.RERANK_GRAY_ZONE
            if top >= high:
                jobs.append((q, name, select_citations(candidates[:config.TOP_K]), None))
            elif top >= low or version:
                contexts = [(r, f'Document: {r.chunk.title}; version: {r.chunk.version}; status: {r.chunk.status}.\n{r.chunk.text}' if version else r.chunk.text) for r in candidates]
                jobs.append((q, name, contexts, []))
    # Qwen span judge, then Gemma fallback judges, preserving the exact functions and cache keys.
    span = {}
    for q, name, candidates, pending in jobs:
        if pending is not None:
            for r, text in candidates:
                span[q, text] = llm.span_judge(q, text)
    print('span requests ready', flush=True)
    for q, name, candidates, pending in jobs:
        if pending is None:
            selected = candidates
        else:
            selected = []
            for r, text in candidates:
                accepted = span[q, text] or llm.yesno_judge(q, text, config.RERANK_YESNO_MODEL)
                if not accepted and config.YESNO_QUESTION_JUDGE and llm.is_yes_no_question(q):
                    accepted = llm.answerability_judge(q, text)
                if not accepted and config.IMPLICIT_BINARY and llm.is_yes_no_question(q):
                    accepted = llm.answerability_judge(q, text, prompt=config.IMPLICIT_BINARY_PROMPT)
                if accepted:
                    selected.append(r)
                    if len(selected) == config.TOP_K:
                        break
        if selected and config.POLARITY_CHECK and llm.is_yes_no_question(q):
            cited = expand_context(selected, corpus[name], config.CONTEXT_NEIGHBORS, config.CONTEXT_POLICY)
            llm.passage_verdict(q, ' '.join(r.chunk.text for r in cited))
    print('fallback and polarity requests ready', flush=True)
