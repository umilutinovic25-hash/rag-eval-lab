"""Run seen sets with original metric functions and save full answers and judge counts."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from src import config,embeddings,llm,rag
from src.chunking import build_chunks
from src.corpus import load_corpus
from src.eval_runner import EVAL_SET_PATH,evaluate_item,load_eval_set,summarise
from src.holdout_runner import HOLDOUT_SET_PATH,TEST_SET_PATH,TEST2_SET_PATH


def run(label,live=False,cache_dir=None):
    root=Path(__file__).parent
    chunks=build_chunks(load_corpus()); by={c.chunk_id:c for c in chunks}
    original=rag.passage_answers; calls=[]
    def judge(*args):
        calls.append(args)
        return original(*args)
    def forbidden(*args):
        raise AssertionError('Model requests forbidden in replay')
    if cache_dir:
        cache_dir.mkdir(parents=True,exist_ok=True)
        embeddings.CACHE_PATH=cache_dir/'embedding_cache.json';llm.CACHE_PATH=cache_dir/'llm_cache.json'
    results={}
    with patch.object(rag,'passage_answers',judge),patch.object(embeddings,'request_embeddings',embeddings.request_embeddings if live else forbidden),patch.object(llm,'request_generation',llm.request_generation if live else forbidden):
        for name,path in [('eval',EVAL_SET_PATH),('holdout',HOLDOUT_SET_PATH),('test1',TEST_SET_PATH),('test2',TEST2_SET_PATH)]:
            rows=[];answers=[];before=len(calls)
            for it in load_eval_set(path):
                ans=rag.build_grounded_answer(it['question'],chunks)
                rows.append(evaluate_item(it,ans,by))
                answers.append({'id':it['id'],'question':it['question'],'answer':ans.answer,'citations':ans.citations,'refused':ans.refused,'fallback':ans.generation_fallback_reason,'trace':getattr(ans,'trace',None)})
            results[name]={'summary':summarise(rows),'results':rows,'answers':answers,'judge_calls':len(calls)-before}
            print(label,name,results[name]['summary'],results[name]['judge_calls'],flush=True)
            (root/f'{label}.json').write_text(json.dumps({'config':config.snapshot(),'sets':results},indent=2)+'\n')
    return results
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('label');p.add_argument('--live',action='store_true');p.add_argument('--cache-dir',type=Path);a=p.parse_args();run(a.label,a.live,a.cache_dir)
