import sys, re, json
from pathlib import Path
REPO=Path(sys.argv[1]); sys.path.insert(0,str(REPO))
from src import config, llm, holdout_runner
from src.chunking import build_chunks
from src.corpus import load_corpus
from src.eval_runner import EVAL_SET_PATH, load_eval_set, normalise
from src.rag import build_grounded_answer
llm.CACHE_PATH=Path(sys.argv[2])/"sweep_llm_cache.json"
STOP=set("a an the is are be to of in on for and or with your you i my can do does it this that as by at from up per not no yes must should will may any there their they we our was were has have had been which what who when where how than then also into about after before same only".split())
def novel(ans, passages, q):
    src=set(re.findall(r"[a-z0-9:]+",(" ".join(passages)+" "+q).lower()))
    words=[w for w in re.findall(r"[a-z0-9:]+",re.sub(r"\[[^\]]*\]","",ans.lower())) if w not in STOP and len(w)>2]
    return [w for w in words if w not in src and w.rstrip("s") not in src and w+"s" not in src]
STRICT=("Answer the question using only facts stated in the passages below. Do not add conditions, people, steps or details "
"that the passages do not state. Reply in one or two short sentences, then list the ids of the passages you used in square brackets, "
"for example [hb-01-chunk-0].\n\nPassages:\n{passages}\n\nQuestion: {question}\nAnswer:")
config.RERANK="llm-gray-zone"; config.ANSWER_MODE="llm"
chunks=build_chunks(load_corpus()); by={c.chunk_id:c.text for c in chunks}
for model,prompt,name in [("gemma3:4b",config.GENERATION_PROMPT,"gemma current"),("gemma3:4b",STRICT,"gemma strict"),("qwen2.5:7b",STRICT,"qwen strict")]:
    config.GENERATION_MODEL=model; config.GENERATION_PROMPT=prompt
    tot=0; out=[]
    for path in (EVAL_SET_PATH, holdout_runner.HOLDOUT_SET_PATH):
        for it in load_eval_set(path):
            if it["expected_behaviour"]!="answer": continue
            r=build_grounded_answer(it["question"],chunks)
            if r.refused: continue
            n=novel(r.answer,[by[c] for c in r.citations],it["question"])
            fact=normalise(it["expected_fact"]) in normalise(r.answer)
            if n: out.append((it["id"],n,r.answer))
            tot+=1
    print(f"== {name}: answers {tot}, with novel words {len(out)}",flush=True)
    for o in out: print("  ",o[0],o[1],"|",o[2].replace("\n"," ")[:150])
