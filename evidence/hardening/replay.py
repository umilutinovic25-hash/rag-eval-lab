"""Replay all four seen sets; forbid network, keep historical files unchanged."""
import json
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from src import embeddings,llm
from src.eval_runner import run_eval
from src.eval_compare import compare_runs, format_comparison
from src.holdout_runner import run_holdout,HOLDOUT_SET_PATH,TEST_SET_PATH,TEST2_SET_PATH

def replay(label):
    root=Path(__file__).parent
    with patch.object(embeddings,'request_embeddings',side_effect=AssertionError('Network forbidden')),patch.object(llm,'request_generation',side_effect=AssertionError('Network forbidden')):
        for name,path in [('eval',None),('holdout',HOLDOUT_SET_PATH),('test1',TEST_SET_PATH),('test2',TEST2_SET_PATH)]:
            run=run_eval() if path is None else run_holdout(path)
            (root/f'{name}-{label}.json').write_text(json.dumps(run,indent=2)+'\n')
            old=json.loads((root/f'{name}-before.json').read_text())
            run=json.loads(json.dumps(run))
            report=compare_runs(old,run)
            (root/f'{name}-{label}-compare.txt').write_text(format_comparison(report,old,run)+'\n')
            print(name, run['summary'],report)
if __name__=='__main__': replay(sys.argv[1])
