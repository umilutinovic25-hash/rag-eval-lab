"""Source-bound Serbian companion, never silently substituted for an updated source."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re

PATH = Path(__file__).resolve().parents[1] / 'data/sr-handbook.json'
_CYRILLIC = 'абвгдђежзијклљмнњопрстћуфхцчџш'
_LATIN = ['a','b','v','g','d','đ','e','ž','z','i','j','k','l','lj','m','n','nj','o','p','r','s','t','ć','u','f','h','c','č','dž','š']
TRANSLITERATE = str.maketrans(dict(zip(_CYRILLIC, _LATIN)))
REVIEW_STATUS = 'assistant_translation_pending_human_review'


def latin(text):
    return text.casefold().translate(TRANSLITERATE)


def language_for(question, choice='auto'):
    if choice not in ('auto', 'en', 'sr'):
        raise ValueError('Nepoznat jezik. Izaberite auto, sr ili en.')
    if choice != 'auto':
        return choice
    if re.search(r'[а-яђјљњћџčćšžđ]|\b(?:koliko|kako|gde|sta|koji|koja|koje|mogu|radim|obuke|podrska|zaposleni)\b', question, re.I):
        return 'sr'
    return 'en'


def localized_chunks(chunks):
    data = json.loads(PATH.read_text())
    localized = []
    for chunk in chunks:
        item = data['chunks'].get(chunk.chunk_id)
        if not item or any(item.get(k) != getattr(chunk, k) for k in ('doc_id', 'version', 'status')) or item.get('source_sha256') != hashlib.sha256(chunk.text.encode()).hexdigest():
            raise ValueError('Srpski prevod ne odgovara trenutnoj verziji izvora. Koristite engleski dok se prevod ne ažurira.')
        if not isinstance(item.get('text'), str) or not item['text'].strip():
            raise ValueError('Nedostaje tekst srpskog prevoda.')
        localized.append(replace(chunk, text=item['text']))
    return localized


def retrieval_question(question):
    text = latin(question)
    text = re.sub(r'\b(?:radim|raditi|radimo|rad)\s+od\s+ku[cć]e\b', 'rad na daljinu', text)
    text = re.sub(r'\bzamenim laptop\b', 'zamena laptopa', text)
    return text
