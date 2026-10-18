"""Deterministic synthetic probes plus read-only diagnostics of seen cached questions.
Run from the repo root: python evidence/audit2-2026-10-18/probe.py
No live model requests; no pipeline, cache, or question-set edits.
"""
import io
import json
from pathlib import Path
import sys
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src import config, embeddings, experiment_runner, llm, rag
from src.chunking import Chunk, build_chunks
from src.corpus import load_corpus
from src.eval_runner import load_eval_set
from src.holdout_runner import HOLDOUT_SET_PATH, TEST_SET_PATH, TEST2_SET_PATH
from src.retrieval import RetrievalResult, retrieve_top_k


def emit(name, value):
    print(name, json.dumps(value, ensure_ascii=False, allow_nan=True))


chunks = build_chunks(load_corpus())
cache = embeddings.load_cache(llm.CACHE_PATH)
items = {item['id']: item for path in [HOLDOUT_SET_PATH, TEST_SET_PATH, TEST2_SET_PATH] for item in load_eval_set(path)}
with patch.object(embeddings, 'request_embeddings', side_effect=AssertionError('No network')), patch.object(llm, 'request_generation', side_effect=AssertionError('No network')):
    for key in ['T02', 'U07', 'U11', 'U13']:
        item = items[key]
        rows = []
        for rank, candidate in enumerate(retrieve_top_k(item['question'], chunks, k=5), start=1):
            if item['expected_fact'].lower() not in candidate.chunk.text.lower() or candidate.chunk.doc_id not in item['expected_doc_ids']:
                continue
            span = config.RERANK_SPAN_PROMPT.format(question=item['question'], passage=candidate.chunk.text)
            yesno = config.RERANK_PROMPT.format(question=item['question'], passage=candidate.chunk.text)
            rows.append({'rank': rank, 'id': candidate.chunk.chunk_id,
                         'span_reply': cache.get(llm.cache_key(config.RERANK_MODEL, span, 40)),
                         'yesno_reply': cache.get(llm.cache_key(config.RERANK_YESNO_MODEL, yesno, 3))})
        emit('GOLD_CANDIDATE_' + key, rows)
    result = rag.build_grounded_answer(items['H20']['question'], chunks)
    emit('H20_CACHED_ANSWER', result.answer)
    previous = next(c.text for c in chunks if c.chunk_id == 'hb-01-chunk-2')
    emit('H20_PREVIOUS_CHUNK', previous)

c = Chunk('a', 'd', 'T', '2026', 'current', 'Passwords must be changed every 90 days.')
for text in ['Passwords must be changed every 90 years [a].', 'Do not change passwords every 90 days [a].', 'Passwords must be changed every ninety years [a].']:
    emit('FORMAL_VALIDATION', {'answer': text, 'issue': rag.generation_issue(text, [RetrievalResult(c, .9)])})

candidates = [RetrievalResult(Chunk(str(i), 'd', 'T', '2026', 'current', f'text{i}'), .6) for i in range(5)]
calls = []
with patch.object(rag, 'retrieve_top_k', return_value=candidates), patch.object(rag, 'passage_answers', side_effect=lambda q, p: calls.append(p) or True), patch.object(config, 'ANSWER_MODE', 'extractive'):
    result = rag.build_grounded_answer('q', [])
    emit('EAGER_JUDGE_CALLS', {'citations': len(result.citations), 'calls': len(calls)})

emit('UNRELATED_NEGATION_REJECTS_VALID_SPAN', llm.span_is_in_passage('parking costs 10 EUR', 'No annual fee applies; parking costs 10 EUR.'))
# JSON NaN is deliberately preserved as observed output of the current arithmetic.
emit('FINITE_VECTOR_OVERFLOW_COSINE', embeddings.cosine([1e308], [1e308]))

payload = {'response': 'According to [a], you may', 'done': True, 'done_reason': 'length'}
with patch.object(llm.urllib.request, 'urlopen', return_value=io.BytesIO(json.dumps(payload).encode())):
    text = llm.request_generation('fake', 'fake', 80)
    emit('TRUNCATION_NOT_FLAGGED', {'text': text, 'issue': rag.generation_issue(text, [RetrievalResult(c, .9)])})


def fake_run(*args):
    result = rag.build_grounded_answer('Question?', [c])
    return {'fallback': result.generation_fallback_reason}


with patch.object(config, 'ANSWER_MODE', 'llm'), patch.object(config, 'RERANK', None), patch.object(rag, 'retrieve_top_k', return_value=[RetrievalResult(c, .9)]), patch.object(experiment_runner, 'model_identity', return_value={'status': 'observed', 'models': {}, 'ollama_version': 'fake'}), patch.object(experiment_runner, 'run_eval', side_effect=fake_run), patch.object(experiment_runner, 'run_holdout', side_effect=fake_run), patch.object(llm, 'request_generation', side_effect=llm.LLMError('simulated service failure')):
    report = experiment_runner.execute('cold')
    emit('SIMULATED_COLD_WITH_FAILED_GENERATION', {'requests': report['manifest']['request_totals'], 'fallbacks': {n: r['run']['fallback'] for n, r in report['runs'].items()}})
