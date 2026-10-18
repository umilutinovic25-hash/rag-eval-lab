"""Explainable claim diagnostics, not a semantic truth classifier."""
import re
from .claim_checks import claim_risks
from .language_tools import fold


def primary_answer(text):
    return re.split(r'\nSource \[', text)[0].replace('Grounded response based on retrieved context:', '').strip()


def audit_answer(question, answer, chunks):
    sources = {c.chunk_id: c.text for c in chunks}
    body = primary_answer(answer)
    # Keep trailing markers attached to the preceding sentence.
    parts = re.split(r'(?<=[.!?])\s+(?=\w)|\n+', body)
    claims = []
    for part in parts:
        ids = re.findall(r'\[([^\[\]]+)\]', part)
        text = re.sub(r'\[[^\[\]]+\]', '', part).strip()
        if not text:
            continue
        passages = [sources[i] for i in ids if i in sources]
        reasons = ['unknown_citation'] if set(ids)-sources.keys() else []
        if not ids:
            reasons.append('unlinked_claim')
        reasons += claim_risks(text, passages) if passages else []
        literal = any(fold(text).strip(' .') in fold(p).strip(' .') for p in passages)
        claims.append(dict(text=text, citations=ids, status='risk' if reasons else 'literal' if literal else 'review', reasons=sorted(set(reasons))))
    requested = []
    q = fold(question)
    if re.search(r'\bwhere\b|gde', q):
        requested.append(('location', bool(re.search(r'portal|floor|desk|hardware|sprat|recepc|aplikacij', body, re.I))))
    if re.search(r'how long|duration|koliko.*(?:traje|vremena)', q):
        requested.append(('duration', bool(re.search(r'\d+\s+(?:business\s+)?(?:days?|hours?|weeks?|months?|dana|sati|nedelj)', body, re.I))))
    return dict(version='heuristic-v1', caveat='Heuristički pregled; oznaka literal potvrđuje prepisan tekst, ne relevantnost ili semantičku potpunost.', claims=claims,
                risk_count=sum(c['status']=='risk' for c in claims), review_count=sum(c['status']=='review' for c in claims),
                completeness=[dict(part=p, present=v) for p,v in requested])
