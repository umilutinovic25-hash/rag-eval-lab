"""Small, auditable language helpers; no unrestricted query rewriting."""
import re
import unicodedata
from .localization import latin

TYPOS = {'laptpo':'laptop','lapotp':'laptop','replacment':'replacement','passwrod':'password','traning':'training','budegt':'budget','parkign':'parking','hardwrae':'hardware','aproval':'approval'}


def fold(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', latin(text).casefold().replace('đ', 'dj')) if not unicodedata.combining(c))


def normalise_query(text):
    text = fold(text)
    text = re.sub(r'\bwfh\b', 'work from home', text)
    text = re.sub(r'\bpto\b', 'annual leave', text)
    def repair(match):
        word = match[0]
        return TYPOS.get(word,word)
    return re.sub(r'\b[a-z]+\b', repair, text)


def linguistic_match(expected, actual):
    """Supplemental v1 contiguous token check, with narrowly scoped SR endings."""
    def tokens(text):
        words = re.findall(r'\w+', fold(text))
        stems = {'licna': 'licn', 'licnu': 'licn', 'licne': 'licn', 'kartica': 'kartic', 'karticu': 'kartic', 'kartice': 'kartic', 'portal':'portal','portalu':'portal','portala':'portal'}
        return [stems.get(w, w) for w in words]
    wanted = tokens(expected)
    if not wanted:
        return False
    for sentence in re.split(r'[.!?\n]', actual):
        source = tokens(sentence)
        if any(w in source for w in ('not', 'never', 'ne', 'nije', 'nisu', 'bez')) and not any(w in wanted for w in ('not', 'never', 'ne', 'nije', 'nisu', 'bez')):
            continue
        if any(source[i:i+len(wanted)] == wanted for i in range(len(source)-len(wanted)+1)):
            return True
    return False
