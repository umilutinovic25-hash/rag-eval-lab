"""Empty-application-cache repeatability probe; never downloads models."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from . import web, operation
from .library import sha

QUESTIONS=['How long does laptop replacement take?','What are the IT support hours?']

def execute(repeats=3):
    if not isinstance(repeats,int) or isinstance(repeats,bool) or not 2<=repeats<=3:
        raise ValueError('Broj ponavljanja mora biti 2 ili 3.')
    rows=[]
    for index in range(repeats):
        with tempfile.TemporaryDirectory(prefix='izvor-empty-cache-') as temp:
            directory=Path(temp)
            for name in ('embedding_cache.json','llm_cache.json','llm_cache-metadata.json'):
                (directory/name).write_text('{}')
            for question in QUESTIONS:
                operation.progress('stability',f'Ponavljanje {index+1}/{repeats}: {question}')
                # Both cache paths are set inside chat's serialized scope.
                with patch.object(web,'RUNTIME_DIR',directory):
                    result=web.chat_payload(question,'verified','en')
                rows.append({'repeat':index+1,'question':question,'result':result})
    groups=[]
    for question in QUESTIONS:
        results=[r['result'] for r in rows if r['question']==question]
        signatures={sha({k:r[k] for k in ('answer','citations','refused')}) for r in results}
        groups.append({'question':question,'distinct_outputs':len(signatures),'stable':len(signatures)==1,'seconds':[r['seconds'] for r in results]})
    return {'kind':'stability','created_at':datetime.now(timezone.utc).isoformat(),'repeats':repeats,'rows':rows,'groups':groups,
            'requests':{k:sum(r['result']['usage']['requests'][k] for r in rows) for k in ('embeddings','llm')},
            'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((web.ROOT/'src').glob('*.py'))},
            'note':'Keš je prazan na početku svakog ponavljanja, zajednički za dva upita u tom ponavljanju. Ollama može ostati učitana u memoriji. Ovo nije hardverski cold-start niti dokaz opšte tačnosti.', 'trace':[]}

def supplemental(report):
    from .language_tools import linguistic_match
    from .acceptance_runner import answer_fingerprint
    rows=[]
    for row in report['results']:
        answer=(row.get('result') or {}).get('answer','')
        facts={fact:linguistic_match(fact,answer) for fact in row['facts']}
        rows.append({'id':row['id'],'historical_pass':row['automatic_checks_pass'],'facts':facts,'supplemental_pass':bool(row['behaviour'] and row['expected_source'] and all(facts.values()))})
    return {'grader':'sr-contiguous-inflection-v1','historical_answers_sha256':answer_fingerprint(report['results']),'historical_summary':report['summary'],
            'passed':sum(r['supplemental_pass'] for r in rows),'total':len(rows),'rows':rows,
            'note':'Dopunska analiza istih istorijskih odgovora. Ne menja zamrznuti skup ni prethodni 23/24 rezultat; nije ljudska ocena.'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repeats',type=int,default=3)
    parser.add_argument('--supplemental',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    report=supplemental(json.loads(args.supplemental.read_text())) if args.supplemental else execute(args.repeats)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print({k:v for k,v in report.items() if k in ('requests','groups','passed','total','grader')},flush=True)

if __name__=='__main__':main()
