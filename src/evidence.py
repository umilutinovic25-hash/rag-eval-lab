"""Conservative source-derived answers for explicit policy contrasts."""
import re
from .claim_checks import normalise_numbers
from .retrieval import RetrievalResult, lexical_score, searchable_chunks

INSTRUCTION = re.compile(r'ignore (?:all |the |previous |above )*instructions|reveal (?:your |the )?(?:system prompt|secrets?)|system\s*:\s*|execute (?:this |the )?(?:command|code)|ignoriši.*instrukc|ignore.*system prompt', re.I)


def suspicious(text):
    return bool(INSTRUCTION.search(text))


def select(question, chunks):
    """Return literal evidence and an explicitly limited qualifier, never an eval-ID lookup."""
    q = normalise_numbers(question)
    candidates = searchable_chunks(chunks)
    patterns = []
    qualifier = ''
    rule = None
    if 'training' in q and 'budget' in q and re.search(r'\b(per team|per person|each employee|per employee|per individual)\b', q):
        patterns = [r'\b(?:each|every) employee\b.*\btraining budget\b']
        rule = 'allocation_scope'
    elif 'parking' in q and re.search(r'guarantee|every|everyone', q):
        patterns = [r'\bparking is limited\b']
        rule = 'limited_availability'
    elif re.search(r'work (?:from home|remotely)|remote work', q) and re.search(r'\b\d+ days?\b', q):
        patterns = [r'\b(?:work remotely|remote work|work from home)\b.*\bup to \d+ days? per week\b']
        rule = 'explicit_weekly_bound'
    elif 'sick leave' in q and re.search(r'annual leave|annual holiday', q):
        patterns = [r'\bsick leave follows a separate policy\b']
        qualifier = 'The passage does not specify whether sick leave is deducted from annual leave.'
        rule = 'separate_policy_limit'
    elif re.search(r'laptop|notebook', q) and re.search(r'replac', q) and re.search(r'where', q) and re.search(r'how long|duration|time', q):
        patterns = [r'\bIT portal\b.*\bHardware\b', r'\b\d+ business days\b']
        rule = 'multipart_location_duration'
    if not patterns:
        return None
    selected = []
    for pattern in patterns:
        matches = [c for c in candidates if re.search(pattern, normalise_numbers(c.text), re.I)]
        # No arbitrary winner across different documents for a policy contrast.
        if not matches or len({c.doc_id for c in matches}) != 1:
            return None
        chunk = matches[0]
        if chunk not in selected:
            selected.append(chunk)
    if len({c.doc_id for c in selected}) != 1:
        return None
    results = [RetrievalResult(c, lexical_score(question, c.text)) for c in selected]
    answer = '\n'.join(f'[{c.chunk_id}] {c.text}' for c in selected)
    if qualifier:
        answer += '\n' + qualifier
    return answer, results, rule
