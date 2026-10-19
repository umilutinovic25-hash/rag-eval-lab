"""Local, same-origin web interface. Start with: python -m src.web."""
import argparse
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import shutil
from pathlib import Path
import threading
import time
from urllib.parse import unquote, urlsplit
import urllib.request

from . import config, embeddings, llm, rag, localization, operation, model_identity
from .store import Store
from .library import Library, sha
from .quality import audit_answer
from .language_tools import normalise_query, fold
from .jobs import JobManager, JobCapacityError
from .chunking import build_chunks
from .corpus import load_corpus

ROOT = Path(__file__).resolve().parents[1]
BASE_CONFIG = config.snapshot()
PIPELINE_LOCK = threading.RLock()
RUNTIME_DIR = ROOT / 'data/runtime'
SAVED_EVALUATION = ROOT / 'evidence/expansion/final.json'
EXTENDED_EVALUATION = ROOT / 'evidence/upgrade/final-all-sets.json'
# Honest status of every set: a set stops being blind once it has been run and looked at.
SET_NOTES = {
    'eval': ('Obavezni skup', 'viđen'), 'holdout': ('Holdout', 'viđen'), 'test': ('Dodatni test 1', 'viđen'),
    'test2': ('Dodatni test 2', 'viđen'), 'test3': ('Slepi test 3', 'viđen posle prvog pokretanja'),
    'test4': ('Slepi test 4', 'viđen posle prvog pokretanja'),
    'test5': ('Slepi test 5', '36 od 40 pitanja novo; 4 ponovljena iz viđenih skupova'),
    'test6': ('Nezavisan korpus (test 6)', 'drugi korpus, viđen posle prvog pokretanja'),
    'inject': ('Prompt injection', 'viđen'), 'inject2': ('Prompt injection 2', 'zaštita pisana posle prvog skupa'),
}


def extended_payload(data):
    sets = data['candidates']['shipped']['sets']
    rows = []
    for name, run in sets.items():
        label, note = SET_NOTES.get(name, (name, ''))
        summary = run['summary']
        rows.append(dict(name=name, label=label, note=note, passed=summary['passed'], total=summary['total'],
                         failed=run['failed'], citation_precision=summary.get('mean_citation_precision')))
    return dict(created_at=data.get('created_at'), sets=rows)
BASELINE_EVALUATION = ROOT / 'evidence/expansion/baseline.json'


@contextmanager
def pipeline_lock():
    # A legacy synchronous call can own the lock while a cancellable job waits.
    operation.progress('waiting', 'Čekam završetak prethodne lokalne obrade.')
    while not PIPELINE_LOCK.acquire(timeout=.1):
        operation.check()
    try:
        operation.check()
        yield
    finally:
        PIPELINE_LOCK.release()


@contextmanager
def profile_scope(profile):
    """The CLI pipeline uses globals; serialize requests and always restore them."""
    if profile not in ('current', 'offline', 'baseline', 'verified'):
        raise ValueError('Nepoznat režim rada.')
    with pipeline_lock():
        previous = config.snapshot()
        try:
            for key, value in BASE_CONFIG.items():
                setattr(config, key, value)
            config.apply_profile(profile)
            yield
        finally:
            for key, value in previous.items():
                setattr(config, key, value)


def documents_payload():
    with profile_scope('current'):
        chunks = build_chunks(load_corpus())
        return [dict(asdict(doc), chunks=[asdict(c) for c in chunks if c.doc_id == doc.doc_id])
                for doc in load_corpus()]


@contextmanager
def runtime_caches():
    """Run under PIPELINE_LOCK; preserve historical experiment caches."""
    previous = embeddings.CACHE_PATH, llm.CACHE_PATH
    directory = RUNTIME_DIR
    directory.mkdir(parents=True, exist_ok=True)
    for source in (*previous, llm.metadata_path()):
        destination = directory / source.name
        if source.exists() and not destination.exists():
            shutil.copyfile(source, destination)
    embeddings.CACHE_PATH, llm.CACHE_PATH = (directory / p.name for p in previous)
    try:
        yield
    finally:
        embeddings.CACHE_PATH, llm.CACHE_PATH = previous


def profile_identity(profile):
    identity = {'status':'historical_alias_cache_unknown_provenance','models':{}}
    if profile=='verified':
        identity_file=RUNTIME_DIR/'model-identity.json'
        try:
            identity=model_identity.observe()
            identity_file.parent.mkdir(parents=True,exist_ok=True)
            embeddings.save_cache(identity,identity_file)
        except (OSError, ValueError, KeyError, TypeError):
            if not identity_file.exists():raise ValueError('Provereni režim zahteva prvo opažanje digesta kroz pokrenutu Ollama-u.')
            identity={**json.loads(identity_file.read_text()),'status':'offline_last_observed'}
    return identity


def chat_payload(question, profile='current', language='auto', filters=None, library=None):
    if not isinstance(question, str) or not question.strip() or len(question) > 2000:
        raise ValueError('Unesite pitanje od 1 do 2000 znakova.')
    started = time.perf_counter()
    language = localization.language_for(question, language)
    with profile_scope(profile), runtime_caches(), model_identity.bind((identity:=profile_identity(profile)) if profile=='verified' else None), operation.measure() as usage:
        if profile!='verified':identity=profile_identity(profile)
        operation.progress('retrieval', 'Pretražujem izvorne odlomke.')
        chunks = library.chunks(filters) if library else build_chunks(load_corpus())
        selected_docs=library.selected(filters) if library else [asdict(d) for d in load_corpus()]
        by_id = {c.chunk_id: c for c in chunks}
        query, translated = question.strip(), {}
        normalized=normalise_query(query)
        if normalized != fold(query):query=normalized
        if language == 'sr':
            chunks = localization.localized_chunks(chunks)
            translated = {c.chunk_id: c.text for c in chunks}
            query = localization.retrieval_question(query)
            config.ANSWER_MODE = 'extractive'
        conflicts=library.conflicts(selected_docs) if library else []
        meaningful=set(normalise_query(question).split())-{'is','the','a','for','of','what','how','policy','do','i','can'}
        conflicts=[c for c in conflicts if meaningful & set(normalise_query(c['title']).split())]
        if conflicts:
            involved={i for c in conflicts for i in c['documents']}
            result=rag.RagAnswer('Pronađeni su mogući sukobi važećih politika. Pregledajte oba izvora u Radionici pre odgovora.',[c.chunk_id for c in chunks if c.doc_id in involved],True,[],trace=[{'stage':'conflict','conflicts':conflicts}], disposition='conflict')
        else:
            result = rag.build_grounded_answer(query, chunks)
        operation.check()
        answer = result.answer
        if language == 'sr' and result.disposition not in ('clarification','conflict'):
            answer = ('Nemam dovoljno dokaza u dostupnom priručniku da odgovorim na ovo pitanje.' if result.refused else
                      answer.replace('Grounded response based on retrieved context:', 'Odgovor iz prevedenih izvornih odlomaka:', 1))
        def source(chunk_id):
            return dict(asdict(by_id[chunk_id]), **({'translated_text': translated[chunk_id]} if translated else {}))
        quality=audit_answer(question,answer,[c for c in chunks if c.chunk_id in result.citations])
        provenance=dict(corpus_sha256=sha(selected_docs),config_sha256=sha(config.snapshot()),config=config.snapshot(),model_identity=identity,
                        filters=filters or {},cache_policy='digest_and_options' if profile=='verified' else 'legacy_alias',language=language)
        payload=dict(answer=answer, refused=result.refused,
                    citations=[source(c) for c in result.citations],
                    retrieved=[dict(source(r.chunk.chunk_id), score=r.score) for r in result.retrieved],
                    trace=result.trace, fallback=result.generation_fallback_reason,
                    question=question.strip(), profile=profile, language=language, retrieval_question=query,
                    translation_review_status=localization.REVIEW_STATUS if language == 'sr' else None,
                    seconds=round(time.perf_counter() - started, 3),
                    created_at=datetime.now(timezone.utc).isoformat(),quality=quality,usage=usage,provenance=provenance,
                    disposition=result.disposition,clarification=result.clarification)
        payload['answer_sha256']=sha({k:payload[k] for k in ('question','answer','citations','provenance')})
        return payload


def workspace_task(library, kind='chat', **body):
    if kind=='chat':return chat_payload(**body,library=library)
    if kind!='comparison':raise ValueError('Nepoznat tip posla.')
    profiles=body.pop('profiles',None)
    if not isinstance(profiles,list) or len(profiles)!=2 or profiles[0]==profiles[1] or any(p not in ('baseline','current','offline','verified') for p in profiles):
        raise ValueError('Izaberite dva različita podržana profila.')
    results=[chat_payload(**body,profile=p,library=library) for p in profiles]
    if results[0]['provenance']['corpus_sha256']!=results[1]['provenance']['corpus_sha256']:
        raise ValueError('Biblioteka se promenila tokom poređenja. Ponovite poređenje.')
    return dict(kind='comparison',results=results,differences=dict(answer=results[0]['answer']!=results[1]['answer'],citations=[c['chunk_id'] for c in results[0]['citations']]!=[c['chunk_id'] for c in results[1]['citations']],refused=results[0]['refused']!=results[1]['refused']),trace=[])


def evaluation_payload(data, origin):
    """Keep measured provenance and failures; omit bulky cache and prompt contents."""
    manifest = data['manifest']
    return dict(origin=origin, mode=manifest['mode'], created_at=manifest['created_at'],
                revision=manifest['git_revision'], git_dirty=manifest.get('git_dirty'),
                source_sha256=manifest.get('source_sha256', {}),
                cache_sha256=manifest.get('used_cache_sha256', manifest.get('cache_sha256', {})),
                status=data['status'],
                question_set_sha256=manifest['question_set_sha256'],
                requests=manifest.get('request_totals', {}),
                runs={name: {key: value for key, value in run.items() if key in
                             ('status', 'error', 'fallback_count', 'seconds', 'requests')}
                      | {'summary': run['run']['summary'] if run['run'] else None,
                         'results': run['run']['results'] if run['run'] else [],
                         'answers': run.get('answers', [])}
                      for name, run in data['runs'].items()})


class WebServer(ThreadingHTTPServer):
    daemon_threads = True
    block_on_close = False

    def server_close(self):
        if hasattr(self, 'jobs'):
            self.jobs.close()
        super().server_close()


class Handler(BaseHTTPRequestHandler):
    def __init__(self, *args, static_dir=None, **kwargs):
        self.static_dir = Path(static_dir or ROOT / 'frontend/dist').resolve()
        super().__init__(*args, **kwargs)

    def log_message(self, fmt, *args):
        # Never log questions or model responses.
        if not self.path.startswith('/api/status'):
            super().log_message(fmt, *args)

    def reply(self, status, body, content_type='application/json; charset=utf-8'):
        payload = json.dumps(body, ensure_ascii=False).encode() if isinstance(body, (dict, list)) else body
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(payload)

    def valid_host(self):
        port = self.server.server_address[1]
        return self.headers.get('Host') in (f'localhost:{port}', f'127.0.0.1:{port}')

    def do_GET(self):
        if not self.valid_host():
            return self.reply(403, {'error': 'Pristup je dozvoljen samo sa lokalne adrese.'})
        path = urlsplit(self.path).path
        if path.startswith('/api/jobs/'):
            job = self.server.jobs.get(path.removeprefix('/api/jobs/'))
            return self.reply(200, job) if job else self.reply(404, {'error': 'Posao ne postoji ili je istekao. Pošaljite pitanje ponovo.'})
        if path == '/api/workspace':
            probe=ROOT/'evidence/expansion/stability.json'
            return self.reply(200,{**self.server.library.health(),'feedback':self.server.store.all('feedback'),'jobs':self.server.jobs.list(),
                'stability':json.loads(probe.read_text()) if probe.exists() else None})
        if path == '/api/status':
            online = False
            models = []
            try:
                with urllib.request.urlopen('http://127.0.0.1:11434/api/tags', timeout=0.8) as response:
                    models = [m['name'] for m in json.load(response)['models']]
                    online = True
            except (OSError, ValueError, KeyError, TypeError):
                pass
            documents = load_corpus()
            return self.reply(200, dict(ollama=online, models=models,
                                      required_models=['bge-m3', 'qwen2.5:7b', 'gemma3:4b'],
                                      documents=len(documents),
                                      current_documents=sum(doc.status == 'current' for doc in documents)))
        if path == '/api/documents':
            return self.reply(200, {'documents': self.server.documents})
        if path == '/api/evaluations/extended':
            try:
                return self.reply(200, extended_payload(json.loads(EXTENDED_EVALUATION.read_text())))
            except (OSError, ValueError, KeyError, TypeError):
                return self.reply(503, {'error': 'Prošireni rezultati nisu dostupni.'})
        if path in ('/api/evaluations','/api/evaluations/baseline'):
            try:
                source=BASELINE_EVALUATION if path.endswith('/baseline') else SAVED_EVALUATION
                return self.reply(200, evaluation_payload(json.loads(source.read_text()), 'baseline' if path.endswith('/baseline') else 'saved'))
            except (OSError, ValueError, KeyError, TypeError):
                return self.reply(503, {'error': 'Sačuvana evaluacija nije dostupna. Pokrenite novu proveru.'})
        if path.startswith('/api/'):
            return self.reply(404, {'error': 'Nepoznata API putanja.'})
        candidate = (self.static_dir / unquote(path).lstrip('/')).resolve()
        if not candidate.is_relative_to(self.static_dir):
            return self.reply(404, {'error': 'Datoteka ne postoji.'})
        if path == '/':
            candidate = self.static_dir / 'index.html'
        if not candidate.is_file():
            return self.reply(404, {'error': 'Frontend nije izgrađen. Pokrenite npm --prefix frontend run build.'})
        return self.reply(200, candidate.read_bytes(), mimetypes.guess_type(candidate.name)[0] or 'application/octet-stream')

    def do_POST(self):
        if not self.valid_host():
            return self.reply(403, {'error': 'Nedozvoljena adresa.'})
        origin = self.headers.get('Origin')
        if origin and origin not in (f'http://localhost:{self.server.server_address[1]}',
                                     f'http://127.0.0.1:{self.server.server_address[1]}'):
            return self.reply(403, {'error': 'Zahtev mora poticati iz lokalnog interfejsa.'})
        path = urlsplit(self.path).path
        cancel_id = path[len('/api/jobs/'):-len('/cancel')] if path.startswith('/api/jobs/') and path.endswith('/cancel') else None
        if path not in ('/api/chat', '/api/evaluations/run', '/api/jobs', '/api/library/preview', '/api/library/update', '/api/library/compare', '/api/feedback') and not cancel_id:
            return self.reply(404, {'error': 'Nepoznata API putanja.'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length <= 0 or length > (400000 if path in ('/api/library/preview','/api/feedback') else 12000):
                return self.reply(413, {'error': 'Neispravna veličina zahteva.'})
            if self.headers.get_content_type() != 'application/json':
                return self.reply(415, {'error': 'Očekivan je JSON zahtev.'})
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError('Očekivan je JSON objekat.')
            if cancel_id:
                job = self.server.jobs.cancel(cancel_id)
                return self.reply(200, job) if job else self.reply(404, {'error': 'Posao ne postoji ili je istekao.'})
            if path=='/api/library/preview':
                return self.reply(200,{'document':self.server.library.preview(data.get('filename'),data.get('content'),data.get('metadata'))})
            if path=='/api/library/update':
                return self.reply(200,{'document':self.server.library.update(data.get('doc_id'),data.get('changes',{}))})
            if path=='/api/library/compare':
                return self.reply(200,self.server.library.compare(data.get('left'),data.get('right')))
            if path=='/api/feedback':
                label,comment,answer=data.get('label'),data.get('comment',''),data.get('answer')
                if label not in ('incorrect','incomplete','wrong_citation','reviewed') or not isinstance(comment,str) or len(comment)>4000 or not isinstance(answer,dict) or not isinstance(answer.get('answer'),str) or not isinstance(answer.get('question'),str) or len(json.dumps(answer))>300000:
                    raise ValueError('Neispravna lokalna ocena odgovora.')
                import uuid
                record=dict(id=uuid.uuid4().hex,label=label,comment=comment,answer=answer,answer_sha256=sha(answer),created_at=datetime.now(timezone.utc).isoformat(),review_identity='self_reported_local_user')
                self.server.store.put('feedback',record['id'],record)
                return self.reply(200,{'feedback':record})
            if path == '/api/jobs':
                question, profile, language = data.get('question'), data.get('profile', 'current'), data.get('language', 'auto')
                kind=data.get('kind','chat')
                if kind not in ('chat','comparison') or not isinstance(question, str) or not question.strip() or len(question) > 2000 or profile not in ('current', 'offline','baseline','verified'):
                    raise ValueError('Unesite pitanje od 1 do 2000 znakova i ispravan režim.')
                localization.language_for(question, language)
                self.server.library.selected(data.get('filters'))
                body=dict(question=question,language=language,filters=data.get('filters'),kind=kind)
                if kind=='comparison':
                    profiles=data.get('profiles')
                    if not isinstance(profiles,list) or len(profiles)!=2 or profiles[0]==profiles[1] or any(p not in ('current','offline','baseline','verified') for p in profiles):raise ValueError('Izaberite dva različita profila.')
                    body['profiles']=profiles
                else:body['profile']=profile
                return self.reply(202, self.server.jobs.submit(body))
            if path == '/api/chat':
                result = chat_payload(data.get('question'), data.get('profile', 'current'), data.get('language', 'auto'),data.get('filters'),self.server.library)
            else:
                from .experiment_runner import execute
                with profile_scope('current'):
                    result = evaluation_payload(execute('replay'), 'replayed')
            return self.reply(200, result)
        except (ValueError, UnicodeDecodeError) as error:
            return self.reply(400, {'error': str(error)})
        except JobCapacityError as error:
            return self.reply(429, {'error': str(error)})
        except (embeddings.EmbeddingError, llm.LLMError) as error:
            return self.reply(503, {'error': 'Lokalni model nije dostupan za ovo pitanje. Pokrenite Ollama ili izaberite režim Bez modela.', 'detail': str(error)})
        except Exception:
            return self.reply(500, {'error': 'Provera nije završena. Pokušajte ponovo ili koristite režim Bez modela.'})


def make_server(port=8767, static_dir=None, state_dir=None):
    global RUNTIME_DIR
    if state_dir is not None:RUNTIME_DIR=Path(state_dir)
    documents = documents_payload()
    server = WebServer(('127.0.0.1', port), partial(Handler, static_dir=static_dir))
    server.documents = documents
    server.store=Store(RUNTIME_DIR/'workspace.sqlite')
    server.library=Library(server.store)
    server.jobs = JobManager(partial(workspace_task,server.library),store=server.store)
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8767)
    parser.add_argument('--state-dir',type=Path,help='Isolated local library, jobs and runtime caches.')
    args = parser.parse_args()
    server = make_server(args.port,state_dir=args.state_dir)
    print(f'Izvor je dostupan na http://localhost:{server.server_address[1]}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
