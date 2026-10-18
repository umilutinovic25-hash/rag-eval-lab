import sys, re
from pathlib import Path
REPO=Path(sys.argv[1]); sys.path.insert(0,str(REPO))
from src import config, llm, rag, holdout_runner
from src.eval_runner import EVAL_SET_PATH
llm.CACHE_PATH=REPO/"data/llm_cache.json"   # read-mostly; new prompts land here too, cleaned later
W=re.compile(r"[a-z0-9:]+")
POL={"yes","no","you","need","must","can","do","does"}
def check(span,passage,strip):
    if not span or span.strip().upper().startswith("NONE"): return False
    words=W.findall(span.lower())
    if strip:
        while words and words[0] in {"yes","no"}: words=words[1:]
    pw=set(W.findall(passage.lower()))
    return bool(words) and sum(w in pw for w in words)/len(words)>=0.8
SPAN2=("Copy the exact words from the passage that answer the question or that directly help answer it. "
"If the passage does not contain the answer, reply NONE.\n\nPassage: {passage}\nQuestion: {question}\nWords from the passage:")
def span(prompt,strip):
    return lambda q,p: check(llm.generate("qwen2.5:7b",prompt.format(question=q,passage=p),40),p,strip)
def yesno(q,p):
    r=llm.generate("gemma3:4b",config.RERANK_PROMPT.format(question=q,passage=p),3).lower().split()
    return bool(r) and r[0].strip(".,!:") in {"yes","relevant"}
S1=config.RERANK_SPAN_PROMPT
V={"span":span(S1,False),"span+strip":span(S1,True),"span2+strip":span(SPAN2,True),
   "union yesno|span+strip":lambda q,p: span(S1,True)(q,p) or yesno(q,p)}
config.ANSWER_MODE="extractive"
for name,j in V.items():
    rag.passage_answers=j; out=[]; fails=[]
    for path in (EVAL_SET_PATH, holdout_runner.HOLDOUT_SET_PATH, holdout_runner.TEST_SET_PATH):
        r=holdout_runner.run_holdout(path); out.append(f"{r['summary']['passed']}/{r['summary']['total']}"); fails+= [x["id"] for x in r["results"] if not x["pass"]]
    print(f"{name:24} eval {out[0]} holdout {out[1]} test1 {out[2]} fails {fails}",flush=True)
