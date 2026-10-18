"""Conservative lexical checks; these do not establish semantic entailment."""
import re

ONES=dict(zip('zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen'.split(),range(20)))
TENS=dict(zip('twenty thirty forty fifty sixty seventy eighty ninety'.split(),range(20,100,10)))
STOP=set('a an the is are be to of in on for and or with your you my can do does it this that as by at from up per must should will may have has been every'.split())
UNITS=r'eur|dollars?|days?|hours?|weeks?|months?|years?|characters?'
MARKERS=re.compile(r'\[[^\[\]]+\]')


def normalise_numbers(text):
    words=re.sub(r'(?<=\w)-(?=\w)',' ',text.casefold()).split()
    result=[];index=0
    while index<len(words):
        word=words[index]
        if word in TENS:
            value=TENS[word]
            if index+1<len(words) and words[index+1] in ONES and ONES[words[index+1]]<10:
                value+=ONES[words[index+1]];index+=1
            result.append(str(value))
        else:result.append(str(ONES[word]) if word in ONES else word)
        index+=1
    return ' '.join(result)


def quantities(text):
    text=normalise_numbers(text)
    return {(number,unit.rstrip('s')) for number,unit in re.findall(r'\b(\d+)\s+(?:business\s+)?('+UNITS+r')\b',text)}


def has_negation(text):
    text=re.sub(r'^\s*(?:yes|no)\s*[,.:!]\s*','',text,flags=re.I)
    return bool(re.search(r"\b(?:no|not|never|cannot)\b|n['’]t\b",text.casefold()))


def clauses(text):
    return [part.strip() for part in re.split(r'(?<=[.!?])\s+|;\s*|\bbut\b',text,flags=re.I) if part.strip()]


def words(text):
    return set(re.findall(r'[a-z0-9]+',normalise_numbers(text)))-STOP-{'no','not','never','cannot'}


def action_roots(text, negative_only=False):
    """Narrow grammatical heuristic to avoid negation about a different action."""
    text=text.casefold()
    pattern = r"\b(?:cannot|never|not|[a-z]+n['’]t)\s+(?:be\s+)?([a-z]+)" if negative_only else r"\b(?:must|should|may|can|cannot|never|not|is|are)\s+(?:not\s+)?(?:be\s+)?([a-z]+)"
    verbs=re.findall(pattern,text)
    first=re.match(r"\s*([a-z]+)",text)
    if first and not negative_only:verbs.append(first[1])
    def root(word):
        for ending in ('ing','ed','s'):
            if word.endswith(ending) and len(word)>len(ending)+2:
                word=word[:-len(ending)];break
        return word.rstrip('e')
    return {root(v) for v in verbs}


def claim_risks(answer,passages):
    body=MARKERS.sub(' ',answer)
    risks=[]
    if not quantities(body)<=set().union(*(quantities(p) for p in passages)):
        risks.append('unsupported_quantity_unit')
    source_clauses=[c for p in passages for c in clauses(p)]
    for claim in clauses(body):
        terms=words(claim)
        if len(terms)<2:continue
        scored=[(len(terms & words(source))/len(terms),source) for source in source_clauses]
        best=max((score for score,_ in scored),default=0)
        nearest=[source for score,source in scored if score==best]
        if best>=0.6 and nearest and all(has_negation(claim)!=has_negation(source) and action_roots(claim,has_negation(claim)) & action_roots(source,has_negation(source)) for source in nearest):
            risks.append('negation_conflict')
    return sorted(set(risks))
