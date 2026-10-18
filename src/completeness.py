"""Draft completeness rubric, separate from the fixed eval metrics and human review."""
import argparse
import json
from pathlib import Path

from .answer_quality import SETS, model_sentence
from .chunking import build_chunks
from .corpus import load_corpus
from .eval_runner import load_eval_set, normalise
from .rag import build_grounded_answer

RUBRIC_PATH=Path(__file__).resolve().parents[1]/'review/completeness-rubric.json'


def slot_coverage(text, slots):
    return {slot['name']:any(normalise(a) in normalise(text) for a in slot['alternatives']) for slot in slots}


def run(rubric_path=RUBRIC_PATH):
    rubric=json.loads(rubric_path.read_text())
    questions={i['id']:i for path in SETS.values() for i in load_eval_set(path)}
    chunks=build_chunks(load_corpus());by={c.chunk_id:c for c in chunks}
    rows=[]
    for item in rubric['items']:
        question=questions[item['id']]['question']
        result=build_grounded_answer(question,chunks)
        source=' '.join(by[c].text for c in result.citations if by[c].doc_id==item['doc_id'])
        rows.append({'id':item['id'],'question':question,'answer':result.answer,'citations':result.citations,
                     'refused':result.refused,'model_slots':slot_coverage(model_sentence(result.answer),item['slots']) if not result.refused else {},
                     'source_slots':slot_coverage(source,item['slots']),
                     'full_answer_slots':slot_coverage(result.answer,item['slots']) if not result.refused else {},
                     'human_verdict':None})
    return {'rubric_status':rubric['status'],'reviewer':rubric['reviewer'],'semantic_correctness':'not_assessed',
            'interpretation':'Draft substring coverage; not proof of entailment or an approved reference.',
            'ambiguous_items':rubric['ambiguous_items'],'rows':rows}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True);p.add_argument('--rubric',type=Path,default=RUBRIC_PATH);a=p.parse_args()
    report=run(a.rubric);out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n')
    print(report['rubric_status'])
    for row in report['rows']:print(row['id'],'model',row['model_slots'],'sources',row['source_slots'])
if __name__=='__main__':main()
