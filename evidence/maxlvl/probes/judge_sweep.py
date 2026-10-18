import sys, json, shutil
from pathlib import Path
REPO=Path(sys.argv[1]); sys.path.insert(0,str(REPO))
from src import config, llm, holdout_runner
from src.eval_runner import EVAL_SET_PATH
scratch=Path(sys.argv[2]); cache=scratch/"sweep_llm_cache.json"
if not cache.exists(): shutil.copy(REPO/"data/llm_cache.json", cache)
llm.CACHE_PATH=cache
P1=config.RERANK_PROMPT
P3=("You decide whether a passage from an employee handbook answers a question.\n"
"Say yes when the passage states the fact that answers the question, even if the answer is no, is indirect, or uses different words.\n"
"Say no when the passage is only about the same topic but does not give the answer.\n\n"
"Example: Question: Can I bring my bike inside the building? Passage: Bicycles must be left in the outdoor rack. Answer: yes\n"
"Example: Question: How much does the gym cost? Passage: The gym is on floor three. Answer: no\n"
"Example: Question: Is the cafe open on Sundays? Passage: The cafe opens Monday to Saturday. Answer: yes\n\n"
"Question: {question}\nPassage: {passage}\nAnswer:")
config.ANSWER_MODE="extractive"; config.RERANK="llm-gray-zone"
for model in sys.argv[3].split(","):
  for pname,prompt in [("P1",P1),("P3",P3)]:
    config.RERANK_MODEL=model; config.RERANK_PROMPT=prompt
    e=holdout_runner.run_holdout(EVAL_SET_PATH); h=holdout_runner.run_holdout()
    fe=[r["id"] for r in e["results"] if not r["pass"]]; fh=[r["id"] for r in h["results"] if not r["pass"]]
    print(f"{model:14} {pname} eval {e['summary']['passed']}/12 holdout {h['summary']['passed']}/34  fails {fe+fh}", flush=True)
