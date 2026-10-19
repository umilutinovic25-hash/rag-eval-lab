import json,time,shutil
from pathlib import Path
from src import config
from src.candidate_runner import run_set
from src.retrieval_metrics import SETS, apply_overrides
from src.scratch import use_scratch_caches
from src.chunking import build_chunks
from src.corpus import load_corpus
source=Path('evidence/upgrade/proposal-21-all.json')
while not source.exists() or 'proposal-21' not in json.loads(source.read_text())['candidates']:
 time.sleep(5)
# Separate cache copy, only after the combined run has stopped writing.
shutil.copytree('results/scratch-21-proposal','results/scratch-21-ablate',dirs_exist_ok=True)
use_scratch_caches(Path('results/scratch-21-ablate'))
chunks=build_chunks(load_corpus())
out={'protocol':'Independent switches, unchanged prompts; reject on regression, no tuning.', 'candidates':{}}
for name,overrides in {
 'version-only':{'VERSION_CONTEXT':True,'EVIDENCE_RELEVANCE':False,'IMPLICIT_BINARY':False},
 'relevance-only':{'VERSION_CONTEXT':False,'EVIDENCE_RELEVANCE':True,'IMPLICIT_BINARY':False},
 'implicit-only':{'VERSION_CONTEXT':False,'EVIDENCE_RELEVANCE':False,'IMPLICIT_BINARY':True},
}.items():
 apply_overrides(overrides)
 out['candidates'][name]={'overrides':overrides,'sets':{}}
 for s in SETS:
  result=run_set(s,chunks)
  out['candidates'][name]['sets'][s]=result
  Path('evidence/upgrade/ablations-21.json').write_text(json.dumps(out,indent=2))
  print(name,s,result['summary']['passed'],flush=True)
