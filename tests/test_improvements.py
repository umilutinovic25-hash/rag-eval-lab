from unittest.mock import patch
import pytest
from src import config, rag
from src.chunking import Chunk
from src.retrieval import RetrievalResult


@pytest.mark.parametrize('accepted,expected_calls', [({'0','1'},2),({'1','3'},4),(set(),5)])
def test_judge_stops_after_top_k_acceptances(monkeypatch,accepted,expected_calls):
    candidates=[RetrievalResult(Chunk(str(i),'d','T','v','current',str(i)),.6) for i in range(5)]
    monkeypatch.setattr(config,'RETRIEVAL_MODE','semantic')
    monkeypatch.setattr(config,'RERANK','llm-gray-zone')
    monkeypatch.setattr(rag,'retrieve_top_k',lambda *a,**k:candidates)
    calls=[]
    monkeypatch.setattr(rag,'passage_answers',lambda q,p:calls.append(p) or p in accepted)
    result=rag.build_grounded_answer('q',[])
    assert len(calls)==expected_calls
    assert result.citations==[c.chunk.chunk_id for c in candidates if c.chunk.chunk_id in accepted][:config.TOP_K]

from src import llm,experiment_runner
import io,json


def test_generation_metadata_survives_cache_and_truncation_falls_back(tmp_path,monkeypatch):
    monkeypatch.setattr(llm,'CACHE_PATH',tmp_path/'llm.json')
    payload={'response':'According to [a], you may','done_reason':'length','eval_count':80}
    original=llm.request_generation
    monkeypatch.setattr(llm.urllib.request,'urlopen',lambda *a,**k:io.BytesIO(json.dumps(payload).encode()))
    # conftest replaces the request function, so bind the real one saved at module import below.
    monkeypatch.setattr(llm,'request_generation',REAL_LLM_REQUEST)
    c=Chunk('a','d','T','v','current','Budget is 800 EUR.')
    monkeypatch.setattr(config,'ANSWER_MODE','llm')
    monkeypatch.setattr(rag,'retrieve_top_k',lambda *a,**k:[RetrievalResult(c,.9)])
    first=rag.build_grounded_answer('Budget?',[c])
    second=rag.build_grounded_answer('Budget?',[c])
    assert first.answer==second.answer and c.text in first.answer
    assert first.generation_fallback_reason=='truncated_answer'
    assert any(e.get('stage')=='generation' and e.get('metadata',{}).get('done_reason')=='length' for e in second.trace)


def test_trace_explains_rejected_candidate(monkeypatch):
    c=Chunk('a','d','T','v','current','Budget is 800 EUR.')
    monkeypatch.setattr(config,'RERANK','llm')
    monkeypatch.setattr(rag,'retrieve_top_k',lambda *a,**k:[RetrievalResult(c,.6)])
    monkeypatch.setattr(rag,'passage_answers',lambda *a:False)
    r=rag.build_grounded_answer('Budget?',[c])
    assert r.refused
    assert {'stage':'judge','chunk_id':'a','accepted':False} in r.trace
    assert r.trace[-1]['reason']=='no_accepted_candidate'


REAL_LLM_REQUEST=llm.request_generation


def test_cold_records_failed_generation_and_keeps_raw_cache(monkeypatch):
    from src.eval_runner import EVAL_SET_PATH
    from src import embeddings
    monkeypatch.setattr(experiment_runner,'model_identity',lambda:{'status':'observed','models':{},'ollama_version':'fake'})
    monkeypatch.setattr(experiment_runner,'SETS',{'eval':EVAL_SET_PATH})
    monkeypatch.setattr(config,'ANSWER_MODE','llm')
    monkeypatch.setattr(embeddings,'request_embeddings',lambda texts:[[1.0] for _ in texts])
    monkeypatch.setattr(config,'RETRIEVAL_MODE','semantic')
    def unavailable(*a):
        raise llm.LLMError('Simulated failure')
    monkeypatch.setattr(llm,'request_generation',unavailable)
    report=experiment_runner.execute('cold')
    assert report['manifest']['request_outcomes']['llm']['failed']>0
    assert report['manifest']['request_outcomes']['llm']['succeeded']==0
    assert report['runs']['eval']['fallback_count']>0
    assert report['runs']['eval']['answers']
    assert report['cold_cache_snapshots']['embeddings']
