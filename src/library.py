"""Explicitly activated local documents and honest effective-date metadata."""
from dataclasses import asdict
from datetime import date, datetime
from zoneinfo import ZoneInfo
import difflib
import hashlib
import json
import re
import uuid

from .corpus import Document, load_corpus
from .chunking import build_chunks
from .evidence import suspicious
from .claim_checks import quantities, scope_risks


def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def validate_metadata(data):
    result = {}
    for key in ('published_on', 'effective_from', 'effective_until'):
        value = data.get(key) or None
        if value is not None:
            if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
                raise ValueError('Datumi moraju imati oblik YYYY-MM-DD.')
            date.fromisoformat(value)
        result[key] = value
    if result['effective_from'] and result['effective_until'] and result['effective_from'] > result['effective_until']:
        raise ValueError('Početak važenja mora biti pre kraja važenja.')
    return result


class Library:
    def __init__(self, store):
        self.store = store

    def documents(self):
        originals = []
        for doc in load_corpus():
            item = asdict(doc)
            metadata = self.store.get('metadata', doc.doc_id) or {}
            if metadata.get('source_sha256') != sha(item):
                metadata = {}
            originals.append({**item, **validate_metadata(metadata), 'origin':'handbook', 'active':True, 'source_sha256':sha(item)})
        return originals + self.store.all('document')

    def preview(self, filename, content, metadata=None):
        if metadata is not None and not isinstance(metadata,dict):raise ValueError('Metapodaci moraju biti JSON objekat.')
        if not isinstance(filename, str) or not isinstance(content, str) or len(content.encode()) > 256000:
            raise ValueError('Dokument može imati najviše 256 kB teksta.')
        ext = filename.lower().rsplit('.', 1)[-1]
        data = dict(metadata or {})
        if ext == 'json':
            parsed = json.loads(content)
            if not isinstance(parsed, dict):
                raise ValueError('JSON dokument mora biti objekat sa text i title poljima.')
            data = {**parsed, **data}
            content = parsed.get('text')
        elif ext not in ('txt','md'):
            raise ValueError('Podržani su samo TXT, MD i JSON tekstualni dokumenti.')
        if not isinstance(content, str) or not content.strip() or '\x00' in content:
            raise ValueError('Dokument mora sadržati neprazan tekst bez NUL znakova.')
        for key, default in (('title', filename), ('section','Sandbox'), ('version','draft'), ('status','current')):
            value = data.get(key, default)
            if not isinstance(value, str) or not value.strip() or len(value)>200:
                raise ValueError('Neispravni metapodaci dokumenta.')
            data[key] = value.strip()
        if data['status'] not in ('current','superseded'):
            raise ValueError('Status mora biti current ili superseded.')
        item = {key:data[key] for key in ('title','section','version','status')}
        item.update(validate_metadata(data))
        item.update(doc_id='local-'+uuid.uuid4().hex, text=content.strip(), origin='sandbox', active=False,
                    quarantined=suspicious(content), source_sha256=sha(content.strip()))
        self.store.put('document', item['doc_id'], item)
        return item

    def update(self, doc_id, changes):
        if not isinstance(doc_id,str) or not isinstance(changes,dict):raise ValueError('Neispravna izmena dokumenta.')
        docs = {d['doc_id']:d for d in self.documents()}
        if doc_id not in docs:
            raise ValueError('Dokument ne postoji.')
        item = docs[doc_id]
        metadata = validate_metadata({**item, **changes})
        if item['origin']=='handbook':
            if set(changes)-set(metadata):
                raise ValueError('Izvorni priručnik je nepromenljiv; menjaju se samo datumi u lokalnom sidecar zapisu.')
            self.store.put('metadata', doc_id, {**metadata,'source_sha256':item['source_sha256']})
            return {**item,**metadata}
        if set(changes)-{'active',*metadata}:
            raise ValueError('Dozvoljene su aktivacija i izmene datuma.')
        active = changes.get('active', item['active'])
        if not isinstance(active, bool):
            raise ValueError('Aktivacija mora biti boolean.')
        if active and item['quarantined']:
            raise ValueError('Sumnjive instrukcije su u karantinu. Uvezite očišćen dokument kao novu verziju.')
        item.update(metadata, active=active)
        self.store.put('document',doc_id,item)
        return item

    def selected(self, filters=None):
        filters = filters or {}
        if not isinstance(filters, dict) or set(filters)-{'topic','doc_ids','as_of','sandbox'}:
            raise ValueError('Nepoznati filteri.')
        topic, ids = filters.get('topic',''), filters.get('doc_ids',[])
        if not isinstance(topic,str) or not isinstance(ids,list) or not all(isinstance(i,str) for i in ids) or not isinstance(filters.get('sandbox',False),bool):
            raise ValueError('Neispravni filteri.')
        as_of = filters.get('as_of') or datetime.now(ZoneInfo('Europe/Belgrade')).date().isoformat()
        validate_metadata({'effective_from':as_of})
        selected = []
        for d in self.documents():
            if not d['active'] or d.get('quarantined') or d['status']!='current':
                continue
            if d['origin']=='sandbox' and not filters.get('sandbox'):
                continue
            if topic and topic!=d['section'] or ids and d['doc_id'] not in ids:
                continue
            if d['effective_from'] and d['effective_from']>as_of or d['effective_until'] and d['effective_until']<as_of:
                continue
            selected.append(d)
        return selected

    def chunks(self, filters=None):
        docs = self.selected(filters)
        fields = ('doc_id','title','section','version','status','text')
        return build_chunks([Document(**{k:d[k] for k in fields}) for d in docs])

    def conflicts(self, docs):
        result=[]
        for i,a in enumerate(docs):
            for b in docs[i+1:]:
                if a['title'].casefold()!=b['title'].casefold() or a['text']==b['text']:
                    continue
                # Both have already passed the same as-of filter.
                if quantities(a['text'])!=quantities(b['text']) or scope_risks(a['text'],b['text']) or scope_risks(b['text'],a['text']):
                    result.append({'documents':[a['doc_id'],b['doc_id']], 'title':a['title'], 'reason':'possible_policy_conflict','heuristic':True,
                                   'evidence':[a['text'],b['text']]})
        return result

    def health(self):
        docs=self.documents(); warnings=[]; seen={}
        ids={d['doc_id'] for d in docs}
        for d in docs:
            reasons=[]; fingerprint=sha(d['text'])
            if fingerprint in seen:reasons.append('duplicate:'+seen[fingerprint])
            seen[fingerprint]=d['doc_id']
            if not d['text'].strip():reasons.append('empty')
            if d['status'] not in ('current','superseded'):reasons.append('unknown_status')
            if suspicious(d['text']):reasons.append('untrusted_instruction')
            if not d['effective_from']:reasons.append('effective_date_unknown')
            for ref in re.findall(r'\[\[([^\]]+)\]\]',d['text']):
                if ref not in ids:reasons.append('missing_reference:'+ref)
            if reasons:warnings.append({'doc_id':d['doc_id'],'reasons':reasons})
        return {'documents':docs,'warnings':warnings,'conflicts':self.conflicts(self.selected({'sandbox':True})), 'note':'Datumi važenja originalnih politika nisu navedeni u zadatku. Godina verzije nije datum početka važenja.'}

    def compare(self, left, right):
        docs={d['doc_id']:d for d in self.documents()}
        if left not in docs or right not in docs or left==right:
            raise ValueError('Izaberite dva različita dokumenta.')
        a,b=docs[left],docs[right]
        return {'left':a,'right':b,'diff':'\n'.join(difflib.unified_diff(a['text'].splitlines(),b['text'].splitlines(),fromfile=a['doc_id'],tofile=b['doc_id'],lineterm='')),
                'note':'Poređenje verzija nije odgovor o aktuelnoj politici. Status i datumi oba izvora su prikazani.'}
