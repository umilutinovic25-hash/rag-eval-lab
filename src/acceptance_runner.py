"""Frozen supplementary checks with explicit AI authorship and human review records."""
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics
import threading
import time
from unittest.mock import patch

from . import embeddings, llm, operation, web
from .experiment_runner import git_revision, model_identity

ROOT = Path(__file__).resolve().parents[1]
SET = ROOT / 'review/acceptance-v2.json'


def answer_fingerprint(rows):
    records = []
    for row in rows:
        result = row.get('result') or {}
        records.append({'id': row['id'], **{key: result.get(key) for key in
                        ('question', 'answer', 'citations', 'refused', 'profile')}})
    return hashlib.sha256(json.dumps(records, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def validate_review(review, expected_ids, expected_answers=None):
    if not isinstance(review, dict):
        raise ValueError('Review must be a JSON object.')
    if expected_answers is not None and review.get('answers_sha256') != expected_answers:
        raise ValueError('Review does not match the exact answers being assessed.')
    reviewer = review.get('reviewer')
    items = review.get('items', [])
    if not isinstance(reviewer, str) or not reviewer.strip():
        raise ValueError('A real reviewer name is required; no automatic human approval.')
    if not isinstance(items, list) or len(items) != len(expected_ids) or {r.get('id') for r in items if isinstance(r, dict)} != set(expected_ids):
        raise ValueError('Every case needs exactly one review decision.')
    if any(r.get('decision') not in ('accepted','rejected','ambiguous') or not isinstance(r.get('comment'), str) or not r['comment'].strip() for r in items):
        raise ValueError('Every decision needs a source-based comment, including accepted answers.')
    return reviewer.strip()


def execute(profile='offline', mode='replay', cache_dir=None):
    source_sha256 = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'src').glob('*.py'))}
    translation_sha256 = hashlib.sha256(web.localization.PATH.read_bytes()).hexdigest()
    sealed = SET.read_bytes()
    fingerprint = hashlib.sha256(sealed).hexdigest()
    if fingerprint != SET.with_suffix('.sha256').read_text().split()[0]:
        raise ValueError('Frozen question set fingerprint differs. Do not silently replace the set.')
    data = json.loads(sealed)
    counts, rows = {'embeddings':0,'llm':0}, []
    def counted(kind, function):
        def call(*args, **kwargs):
            counts[kind] += 1
            if mode == 'replay':
                raise RuntimeError('Replay attempted an uncached model request')
            return function(*args, **kwargs)
        return call
    cache_dir = Path(cache_dir) if cache_dir else ROOT / 'data/runtime/acceptance'
    with ExitStack() as stack:
        stack.enter_context(patch.object(web, 'RUNTIME_DIR', cache_dir))
        with web.profile_scope('current'), web.runtime_caches():
            pass
        cache_before = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in cache_dir.glob('*.json')}
        stack.enter_context(patch.object(embeddings,'request_embeddings',counted('embeddings',embeddings.request_embeddings)))
        stack.enter_context(patch.object(llm,'request_generation',counted('llm',llm.request_generation)))
        for item in data['items']:
            start, before, phases = time.perf_counter(), dict(counts), []
            result, error = None, None
            try:
                with operation.scope(threading.Event(), lambda stage,message: phases.append({'stage':stage,'seconds':round(time.perf_counter()-start,3)}),time.monotonic()+300):
                    result = web.chat_payload(item['question'], profile, item['language'])
            except Exception as exc:
                error = {'type':type(exc).__name__,'message':str(exc)}
            expected_answer = item['expected_behaviour'] == 'answer'
            behaviour = result is not None and result['refused'] != expected_answer
            facts = {fact: bool(result) and fact.casefold() in result['answer'].casefold() for fact in item['required_facts']}
            source = result is not None and (not expected_answer or any(c['doc_id']==item['doc_id'] for c in result['citations']))
            rows.append(dict(id=item['id'],pair=item['pair'],language=item['language'],question=item['question'],
                             behaviour=behaviour,facts=facts,expected_source=source,
                             automatic_checks_pass=bool(behaviour and source and all(facts.values())),
                             semantic_correctness='not_human_assessed',result=result,error=error,
                             seconds=round(time.perf_counter()-start,3),phases=phases,
                             requests={k:counts[k]-before[k] for k in counts}))
    seconds=sorted(r['seconds'] for r in rows)
    return {'manifest':{'created_at':datetime.now(timezone.utc).isoformat(),'git_revision':git_revision(),
                        'question_set_sha256':fingerprint,'frozen_set_verified':True,'profile':profile,'mode':mode,
                        'source_sha256':source_sha256,'translation_sha256':translation_sha256,
                        'answers_sha256':answer_fingerprint(rows),
                        'cache_before_sha256':cache_before,
                        'cache_after_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in cache_dir.glob('*.json')},
                        'independent_blind_evidence':False,'review_status':data['status'],'reviewer':None,
                        'requests':counts,'local_models':model_identity() if mode=='live' else {'status':'not_checked'},
                        'interpretation':'Automatic substring/source checks on an assistant-authored frozen candidate. Cached and live calls are counted; no independent human approval.',
                        'latency_seconds':{'p50':statistics.median(seconds),'p95':seconds[max(0, int(len(seconds)*.95)-1)]}},
            'summary':{'passed_automatic_checks':sum(r['automatic_checks_pass'] for r in rows),'total_language_variants':len(rows),'underlying_cases':len({r['pair'] for r in rows})},'results':rows}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',choices=['offline','current'],default='offline')
    parser.add_argument('--mode',choices=['replay','live'],default='replay')
    parser.add_argument('--cache-dir')
    parser.add_argument('--out',required=True)
    parser.add_argument('--review-template')
    parser.add_argument('--review')
    args=parser.parse_args()
    report=execute(args.profile,args.mode,args.cache_dir)
    ids=[r['id'] for r in report['results']]
    if args.review_template:
        template={'reviewer':'','set_sha256':report['manifest']['question_set_sha256'],'answers_sha256':report['manifest']['answers_sha256'],'items':[{'id':r['id'],'question':r['question'],'answer':r['result']['answer'] if r['result'] else None,'decision':'pending','comment':''} for r in report['results']]}
        Path(args.review_template).write_text(json.dumps(template,ensure_ascii=False,indent=2)+'\n')
    if args.review:
        review=json.loads(Path(args.review).read_text())
        if review.get('set_sha256') != report['manifest']['question_set_sha256']:
            raise ValueError('Human review references another set.')
        report['human_review']={'reviewer':validate_review(review,ids,report['manifest']['answers_sha256']),'record':review,'identity_verification':'self_reported; no independent identity verification'}
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(report['summary'],report['manifest']['requests'],flush=True)


if __name__=='__main__': main()
