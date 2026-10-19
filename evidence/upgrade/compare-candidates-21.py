"""Pair unchanged evaluator pass flags; no new metric or answer grading."""
import json
from pathlib import Path

main = json.loads(Path('evidence/upgrade/proposal-21-all.json').read_text())
ablations = json.loads(Path('evidence/upgrade/ablations-21.json').read_text())
base = main['candidates']['shipped']['sets']
output = {}
for name, candidate in {**main['candidates'], **ablations['candidates']}.items():
    if name == 'shipped':
        continue
    per_set = {}
    for key, run in candidate['sets'].items():
        before = {r['id']: r['pass'] for r in base[key]['results']}
        after = {r['id']: r['pass'] for r in run['results']}
        per_set[key] = {
            'before': base[key]['summary']['passed'], 'after': run['summary']['passed'],
            'fixed': [k for k in before if not before[k] and after[k]],
            'broken': [k for k in before if before[k] and not after[k]],
        }
    output[name] = {'sets': per_set, 'no_regressions': all(not s['broken'] for s in per_set.values())}
Path('evidence/upgrade/comparison-21.json').write_text(json.dumps(output, indent=2))
for name, data in output.items():
    print(name, 'no_regressions:', data['no_regressions'])
    for key, run in data['sets'].items():
        if run['fixed'] or run['broken']:
            print(' ', key, run)
