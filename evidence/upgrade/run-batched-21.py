import importlib.util,json,shutil,subprocess
from pathlib import Path
from src import config
from src.candidate_runner import run_set,CANDIDATES
from src.retrieval_metrics import SETS,apply_overrides
from src.chunking import build_chunks
from src.corpus import load_corpus
from src.scratch import use_scratch_caches,NAMES
spec=importlib.util.spec_from_file_location('prime21','evidence/upgrade/prime-21.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
chunks=build_chunks(load_corpus());new=['test7','near3','implicit3','inject3'];old=[n for n in SETS if n not in new]
base=config.snapshot()
def configure(overrides):
 for k,v in base.items():setattr(config,k,v)
 apply_overrides(overrides)
def save(path,obj):Path(path).write_text(json.dumps(obj,indent=2))
def measure(names,out):
 result={}
 for n in names:
  result[n]=run_set(n,chunks)
  print(n,result[n]['summary']['passed'],flush=True)
 return result
# Continue the interrupted baseline using only its own scratch cache.
configure({});use_scratch_caches(Path('results/scratch-21-before'));mod.prime(new,chunks)
out={'sets':measure(new,None)};save('evidence/upgrade/new-sets-before-21.json',out)
# Copy baseline experiment keys, never data; then run the user-requested candidate command.
for name in NAMES:
 target=Path('results/scratch-21-proposal')/name;src=Path('results/scratch-21-before')/name
 data=json.loads(target.read_text());data.update(json.loads(src.read_text()));target.write_text(json.dumps(data))
configure({});use_scratch_caches(Path('results/scratch-21-proposal'));mod.prime(old,chunks)
# Prime changed prompts before candidate_runner; ordinary old/new prompts are already cached.
configure(CANDIDATES['proposal-21']);mod.prime(list(SETS),chunks)
with open('results/proposal-21.log','w') as f:
 subprocess.run(['.venv/bin/python','-m','src.candidate_runner','--sets',*old,*new,'--candidates','shipped','proposal-21','--scratch','results/scratch-21-proposal','--out','evidence/upgrade/proposal-21-all.json'],stdout=f,stderr=subprocess.STDOUT,check=True)
configure({})
# Fixed independent-switch ablations, defined before looking at any challenge outcome.
shutil.copytree('results/scratch-21-proposal','results/scratch-21-ablate',dirs_exist_ok=True)
use_scratch_caches(Path('results/scratch-21-ablate'));out={'candidates':{}}
for name,overrides in {
 'version-only':{'VERSION_CONTEXT':True},
 'relevance-only':{'EVIDENCE_RELEVANCE':True},
 'implicit-only':{'IMPLICIT_BINARY':True},
}.items():
 configure(overrides);mod.prime(list(SETS),chunks)
 out['candidates'][name]={'overrides':overrides,'sets':measure(list(SETS),None)}
 save('evidence/upgrade/ablations-21.json',out)
# Each cold repeat computes all vectors/judges from scratch, independently, including batching work.
for repeat in (1,2):
 folder=Path(f'results/scratch-21-cold-{repeat}');folder.mkdir(exist_ok=True)
 for name in NAMES:(folder/name).write_text('{}\n')
 configure(CANDIDATES['proposal-21']);use_scratch_caches(folder);mod.prime(new,chunks)
 out={'repeat':repeat,'config':config.snapshot(),'sets':measure(new,None)}
 save(f'evidence/upgrade/cold-21-{repeat}.json',out)
