import json
from pathlib import Path
from src import config
from src.candidate_runner import CANDIDATES,run_set
from src.retrieval_metrics import apply_overrides
from src.scratch import use_scratch_caches,NAMES
from src.chunking import build_chunks
from src.corpus import load_corpus
apply_overrides(CANDIDATES['proposal-21'])
chunks=build_chunks(load_corpus())
for repeat in (1,2):
 folder=Path(f'results/scratch-21-cold-{repeat}')
 folder.mkdir(parents=True,exist_ok=True)
 for name in NAMES:
  (folder/name).write_text('{}\n')
 use_scratch_caches(folder)
 out={'repeat':repeat,'config':config.snapshot(),'sets':{}}
 for name in ('test7','near3','implicit3','inject3'):
  out['sets'][name]=run_set(name,chunks)
  Path(f'evidence/upgrade/cold-21-{repeat}.json').write_text(json.dumps(out,indent=2))
  print(repeat,name,'complete',flush=True)
