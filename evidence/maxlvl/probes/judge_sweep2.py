import sys, json, math, hashlib, re, urllib.request
from pathlib import Path
REPO=Path(sys.argv[1]); sys.path.insert(0,str(REPO))
from src import config, llm, rag, holdout_runner
from src.eval_runner import EVAL_SET_PATH, normalise
from src.embeddings import load_cache, save_cache
scratch=Path(sys.argv[2]); llm.CACHE_PATH=scratch/"sweep_llm_cache.json"
LP=scratch/"sweep_logprob_cache.json"
def call(model,prompt,n,logprobs=False):
    c=load_cache(LP if logprobs else llm.CACHE_PATH); k=hashlib.sha256(f"{model}\n{n}\n{logprobs}\n{prompt}".encode()).hexdigest()
    if k not in c:
        body={"model":model,"prompt":prompt,"stream":False,"options":{"temperature":0,"seed":7,"num_predict":n}}
        if logprobs: body.update(logprobs=True,top_logprobs=10)
        r=json.load(urllib.request.urlopen(urllib.request.Request("http://localhost:11434/api/generate",data=json.dumps(body).encode(),headers={"Content-Type":"application/json"}),timeout=120))
        c[k]= r["logprobs"][0]["top_logprobs"] if logprobs else r["response"].strip()
        save_cache(c, LP if logprobs else llm.CACHE_PATH)
    return c[k]
P4=("Copy the exact words from the passage that answer the question. "
"If the passage does not contain the answer, reply NONE.\n\nPassage: {passage}\nQuestion: {question}\nWords from the passage:")
def toks(s): return re.findall(r"[a-z0-9:]+", s.lower())
def span_judge(model):
    def f(q,p):
        r=call(model,P4.format(question=q,passage=p),40)
        if not r or r.upper().startswith("NONE"): return False
        rt=toks(r); pt=set(toks(p))
        return bool(rt) and sum(t in pt for t in rt)/len(rt)>=0.8
    return f
def lp_judge(model,prompt,thr):
    def f(q,p):
        top=call(model,prompt.format(question=q,passage=p),1,True)
        py=sum(math.exp(t["logprob"]) for t in top if t["token"].strip().lower().startswith("yes"))
        pn=sum(math.exp(t["logprob"]) for t in top if t["token"].strip().lower().startswith("no"))
        return py/(py+pn+1e-12)>=thr
    return f
config.ANSWER_MODE="extractive"; config.RERANK=sys.argv[3]
P1=config.RERANK_PROMPT
variants=[("span qwen7b",span_judge("qwen2.5:7b"))]
for name,j in variants:
    rag.passage_answers=j
    e=holdout_runner.run_holdout(EVAL_SET_PATH); h=holdout_runner.run_holdout()
    fe=[r["id"] for r in e["results"] if not r["pass"]]; fh=[r["id"] for r in h["results"] if not r["pass"]]
    print(f"{name:20} eval {e['summary']['passed']}/12 holdout {h['summary']['passed']}/34 fails {fe+fh}",flush=True)
