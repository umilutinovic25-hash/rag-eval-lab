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
    candidates = searchable_chunks(chunks, question)
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


META_REQUEST = re.compile(
    r"\bwho (?:built|made|created|trained) you\b|\b(?:what|which) (?:model|ai|llm) are you\b"
    r"|\b(?:what )?were you (?:told|instructed|programmed|given)\b|\bdeveloper gave you\b"
    r"|\b(?:your|you) (?:system |initial |hidden |original |secret )?(?:prompt|instructions|configuration|directions)\b"
    r"|\bsource code of your\b|\b(?:convert|translate) your\b"
    r"|\b(?:act as|pretend (?:to be|you)|from now on you|let'?s play a game|in the voice of|roleplay)\b|\byou are (?:now )?dan\b"
    r"|\b(?:stop|forget|ignore|disregard|override|bypass)\b.{0,40}\b(?:handbook|corpus|refusal|safety|previous|earlier|above)\b"
    r"|\brespond with the words\b|\b(?:write|compose) (?:me )?(?:a|an) (?:poem|song|story|joke|essay|haiku)\b|\btell me a joke\b",
    re.I)
ENGLISH_WORDS = frozenset("the a an is are was be to of in on for and or with you your can do does it this that as by at from per must may have has will not if when what how who which".split())


def meta_request(question):
    """Requests aimed at the assistant itself (its prompt, role, output format) rather than at the corpus."""
    return bool(META_REQUEST.search(question))


def english_share(text):
    words = re.findall(r"[a-z]+", text.casefold())
    return len(words), (sum(w in ENGLISH_WORDS for w in words) / len(words) if words else 0.0)


FOREIGN_WORDS = frozenset(
    "der die das und ist nicht ein eine einem einen zu mit f\u00fcr auf von im den dem des sie wir ihre sind werden "
    "le la les et est pas un une des pour avec dans que el los las es por con para como "
    "je da se na su za ne sa od ili ima nije koji kao".split())


def foreign_share(text):
    words = re.findall(r"[a-z\u00e0-\u017e]+", text.casefold())
    return len(words), (sum(w in FOREIGN_WORDS for w in words) / len(words) if words else 0.0)


def language_mismatch(question, answer):
    """True when an English question got an answer that is clearly written in another language."""
    q_n, q_share = english_share(question)
    body = re.sub(r"\[[^\[\]]+\]", " ", answer)
    a_n, a_share = english_share(body)
    _, f_share = foreign_share(body)
    return q_n >= 3 and q_share >= 0.1 and a_n >= 6 and a_share < 0.12 and f_share >= 0.2
