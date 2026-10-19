from pathlib import Path
from src import config, llm
from src.scratch import use_scratch_caches
use_scratch_caches(Path("results/scratch-t3-final"))
from src.chunking import build_chunks
from src.corpus import load_corpus
by={c.chunk_id:c for c in build_chunks(load_corpus())}
cases=[("Are parking spaces assigned to individual people permanently?","hb-09-chunk-1"),
       ("Is the old limit of 2 remote days per week still in force?","hb-03-chunk-0"),
       ("Is the old limit of 2 remote days per week still in force?","hb-03-chunk-2")]
for q,cid in cases:
    p=by[cid].text
    print("Q:",q,"| P:",p)
    print("  span-qwen:",repr(llm.generate(config.RERANK_MODEL,config.RERANK_SPAN_PROMPT.format(question=q,passage=p),40)))
    for m in ("qwen2.5:7b","gemma3:4b"):
        print("  yesno",m,repr(llm.generate(m,config.RERANK_PROMPT.format(question=q,passage=p),3)))
