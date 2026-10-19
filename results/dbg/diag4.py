import json
from pathlib import Path
from src import config, llm
from src.scratch import use_scratch_caches
use_scratch_caches(Path("results/scratch-t4-after"))
from src.chunking import build_chunks
from src.corpus import load_corpus
by={c.chunk_id:c for c in build_chunks(load_corpus())}
q={x["id"]:x for x in json.load(open("eval/test4_set.json"))}
for name in ("before","after"):
    d=json.load(open(f"results/test4-{'before' if name=='before' else 'after'}.json"))
    key="before-yesno3" if name=="before" else "shipped"
    rows=d["candidates"][key]["sets"]["test4"]["results"]
    print("==",name)
    for r in rows:
        if not r["pass"]:
            print(r["id"],q[r["id"]]["question"],"|exp",r["expected"],"got",r["got"],"cited",r["cited_chunk_ids"],[(t["chunk_id"],t["score"]) for t in r["top_k"]])
print()
for i in ("W05","W10","W26","W20","W22"):
    question=q[i]["question"]
    row=next(r for r in json.load(open("results/test4-after.json"))["candidates"]["shipped"]["sets"]["test4"]["results"] if r["id"]==i)
    top=row["top_k"][0]["chunk_id"]
    p=by[top].text
    print(i,question,"\n   top:",top,p)
    print("   3way-gemma:",llm.generate("gemma3:4b",config.YESNO_QUESTION_PROMPT.format(question=question,passage=p),3),
          "| span:",llm.generate(config.RERANK_MODEL,config.RERANK_SPAN_PROMPT.format(question=question,passage=p),40),
          "| yesno-gemma:",llm.generate("gemma3:4b",config.RERANK_PROMPT.format(question=question,passage=p),3))
