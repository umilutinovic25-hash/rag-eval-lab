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
