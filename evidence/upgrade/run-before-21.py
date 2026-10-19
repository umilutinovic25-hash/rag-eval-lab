import json
from pathlib import Path
from src.candidate_runner import run_set
from src.retrieval_metrics import SETS,CORPORA
from src.scratch import use_scratch_caches
from src.chunking import build_chunks
from src.corpus import load_corpus
SETS.update({k:f'{k}_set.json' for k in ('test7','near3','implicit3','inject3')})
CORPORA['test7']='corpus2.json'
use_scratch_caches(Path('results/scratch-21-before'))
chunks=build_chunks(load_corpus())
out={'sets':{}}
for name in ('test7','near3','implicit3','inject3'):
 out['sets'][name]=run_set(name,chunks)
 Path('evidence/upgrade/new-sets-before-21.json').write_text(json.dumps(out,indent=2))
 print(name,'completed',flush=True)
