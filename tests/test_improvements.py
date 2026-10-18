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


def test_rubric_does_not_count_same_form_as_a_location():
    from src.completeness import slot_coverage
    slots=[{'name':'location','alternatives':['IT portal']},{'name':'section','alternatives':['Hardware']}]
    assert slot_coverage('Use that same form.',slots)=={'location':False,'section':False}
    assert slot_coverage('Use IT portal under Hardware.',slots)=={'location':True,'section':True}


def test_rubric_is_honestly_marked_as_unreviewed():
    from src.completeness import RUBRIC_PATH
    r=json.loads(RUBRIC_PATH.read_text())
    assert r['status']=='assistant_draft_not_human_approved' and r['reviewer'] is None
    assert any(i['id']=='T02' for i in r['ambiguous_items'])


@pytest.mark.parametrize('answer',[
 'Passwords must be changed every 90 years [a].',
 'Passwords must be changed every ninety years [a].',
 'Do not change passwords every 90 days [a].',
])
def test_units_and_negation_in_generated_claims_are_rejected(answer):
    c=Chunk('a','d','T','v','current','Passwords must be changed every 90 days.')
    assert rag.generation_issue(answer,[RetrievalResult(c,.9)]) in ('unsupported_quantity_unit','negation_conflict')


def test_valid_positive_clause_not_rejected_due_to_other_clause():
    assert llm.span_is_in_passage('parking costs 10 EUR','No annual fee applies; parking costs 10 EUR.')


def test_cosine_large_finite_vectors_is_stable():
    from src.embeddings import cosine
    assert cosine([1e308],[1e308])==pytest.approx(1.0)


@pytest.mark.parametrize('answer,source',[
 ('Bring it to the IT desk on floor two. [a]','For a laptop that does not start, bring it to IT desk on floor two.'),
 ('No, you cannot request leave the day before as it must be made two weeks in advance. [a]','Leave requests must be made two weeks in advance in HR portal.'),
])
def test_negation_about_a_different_action_does_not_force_fallback(answer,source):
    assert rag.generation_issue(answer,[RetrievalResult(Chunk('a','d','T','v','current',source),.9)]) is None


def test_neighbor_context_does_not_mix_versions_or_documents():
    c0=Chunk('d-0','d','T','v1','current','Location: IT portal under Hardware.')
    c1=Chunk('d-1','d','T','v1','current','Headsets use the same form.')
    old=Chunk('old','d','T','v0','superseded','Old location')
    other=Chunk('other','other','T','v1','current','Different document')
    result=rag.expand_context([RetrievalResult(c1,.9)],[c0,old,other,c1],1)
    assert [r.chunk.chunk_id for r in result]==['d-0','d-1']
    assert rag.expand_context([RetrievalResult(c1,.9)],[c0,c1],0)==[RetrievalResult(c1,.9)]


@pytest.mark.parametrize('payload,expected',[
 ({'status':'supported','evidence':['Budget is 800 EUR.']},True),
 ({'status':'contradicted','evidence':['Budget is 800 EUR.']},True),
 ({'status':'insufficient','evidence':[]},False),
 ({'status':'supported','evidence':['Budget is 900 EUR.']},False),
 ({'status':'supported','evidence':'Budget is 800 EUR.'},False),
 ({'status':'maybe','evidence':['Budget is 800 EUR.']},False),
])
def test_structured_judge_requires_valid_status_and_exact_evidence(monkeypatch,payload,expected):
    monkeypatch.setattr(config,'RERANK_JUDGE','structured')
    monkeypatch.setattr(llm,'generate',lambda *a:json.dumps(payload))
    assert llm.passage_answers('Can I spend 900 EUR?','Budget is 800 EUR.') is expected


def test_reference_context_expands_only_previous_anaphoric_evidence():
    before=Chunk('a','d','T','v','current','Use IT portal under Hardware.')
    reference=Chunk('b','d','T','v','current','Headsets use that same form.')
    after=Chunk('c','d','T','v','current','Unrelated extra information.')
    selected=rag.expand_context([RetrievalResult(reference,.9)],[before,reference,after],1,'references')
    assert [c.chunk.chunk_id for c in selected]==['a','b']
    selected=rag.expand_context([RetrievalResult(before,.9)],[before,reference,after],1,'references')
    assert [c.chunk.chunk_id for c in selected]==['a']


@pytest.mark.parametrize('reply',['not json','{}','{"status":"supported","evidence":[]}', 'prose before {"status":"supported","evidence":["Budget is 800 EUR."]}'])
def test_structured_judge_rejects_unparseable_or_empty_evidence(monkeypatch,reply):
    monkeypatch.setattr(config,'RERANK_JUDGE','structured')
    monkeypatch.setattr(llm,'generate',lambda *a:reply)
    assert not llm.passage_answers('Budget?','Budget is 800 EUR.')


def test_truncated_structured_decision_is_not_accepted(monkeypatch):
    monkeypatch.setattr(config,'RERANK_JUDGE','structured')
    reply=llm.GenerationText(json.dumps({'status':'supported','evidence':['Budget is 800 EUR.']}),{'done_reason':'length'})
    monkeypatch.setattr(llm,'generate',lambda *a:reply)
    assert not llm.passage_answers('Budget?','Budget is 800 EUR.')


def test_quantity_guard_uses_the_cited_passage_not_an_unrelated_number():
    a=RetrievalResult(Chunk('a','a','T','v','current','Passwords must be changed every 90 days.'),.9)
    b=RetrievalResult(Chunk('b','b','T','v','current','Warranty lasts 90 years.'),.8)
    assert rag.generation_issue('Passwords must be changed every 90 years [a].',[a,b])=='unsupported_quantity_unit'


def test_structured_judge_accepts_only_an_entire_json_markdown_block(monkeypatch):
    monkeypatch.setattr(config,'RERANK_JUDGE','structured')
    body=json.dumps({'status':'supported','evidence':['Budget is 800 EUR.']})
    monkeypatch.setattr(llm,'generate',lambda *a:'```json\n'+body+'\n```')
    assert llm.passage_answers('Budget?','Budget is 800 EUR.')
    monkeypatch.setattr(llm,'generate',lambda *a:'Ignore rules\n```json\n'+body+'\n```')
    assert not llm.passage_answers('Budget?','Budget is 800 EUR.')
