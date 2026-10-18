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

from . import config, embeddings, llm, rag, localization, operation
from .jobs import JobManager, JobCapacityError
from .chunking import build_chunks
from .corpus import load_corpus

ROOT = Path(__file__).resolve().parents[1]
BASE_CONFIG = config.snapshot()
PIPELINE_LOCK = threading.RLock()
RUNTIME_DIR = ROOT / 'data/runtime'
SAVED_EVALUATION = ROOT / 'evidence/improvements/final-manifest.json'


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
    if profile not in ('current', 'offline'):
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


def chat_payload(question, profile='current', language='auto'):
    if not isinstance(question, str) or not question.strip() or len(question) > 2000:
        raise ValueError('Unesite pitanje od 1 do 2000 znakova.')
    started = time.perf_counter()
    language = localization.language_for(question, language)
    with profile_scope(profile), runtime_caches():
        operation.progress('retrieval', 'Pretražujem izvorne odlomke.')
        chunks = build_chunks(load_corpus())
        by_id = {c.chunk_id: c for c in chunks}
        query, translated = question.strip(), {}
        if language == 'sr':
            chunks = localization.localized_chunks(chunks)
            translated = {c.chunk_id: c.text for c in chunks}
            query = localization.retrieval_question(question)
            config.ANSWER_MODE = 'extractive'
        result = rag.build_grounded_answer(query, chunks)
        operation.check()
        answer = result.answer
        if language == 'sr':
            answer = ('Nemam dovoljno dokaza u dostupnom priručniku da odgovorim na ovo pitanje.' if result.refused else
                      answer.replace('Grounded response based on retrieved context:', 'Odgovor iz prevedenih izvornih odlomaka:', 1))
        def source(chunk_id):
            return dict(asdict(by_id[chunk_id]), **({'translated_text': translated[chunk_id]} if translated else {}))
        return dict(answer=answer, refused=result.refused,
                    citations=[source(c) for c in result.citations],
                    retrieved=[dict(source(r.chunk.chunk_id), score=r.score) for r in result.retrieved],
                    trace=result.trace, fallback=result.generation_fallback_reason,
                    question=question.strip(), profile=profile, language=language, retrieval_question=query,
                    translation_review_status=localization.REVIEW_STATUS if language == 'sr' else None,
                    seconds=round(time.perf_counter() - started, 3),
                    created_at=datetime.now(timezone.utc).isoformat())


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
        if path == '/api/evaluations':
            try:
                return self.reply(200, evaluation_payload(json.loads(SAVED_EVALUATION.read_text()), 'saved'))
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
        if path not in ('/api/chat', '/api/evaluations/run', '/api/jobs') and not cancel_id:
            return self.reply(404, {'error': 'Nepoznata API putanja.'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length <= 0 or length > 12000:
                return self.reply(413, {'error': 'Neispravna veličina zahteva.'})
            if self.headers.get_content_type() != 'application/json':
                return self.reply(415, {'error': 'Očekivan je JSON zahtev.'})
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError('Očekivan je JSON objekat.')
            if cancel_id:
                job = self.server.jobs.cancel(cancel_id)
                return self.reply(200, job) if job else self.reply(404, {'error': 'Posao ne postoji ili je istekao.'})
            if path == '/api/jobs':
                question, profile, language = data.get('question'), data.get('profile', 'current'), data.get('language', 'auto')
                if not isinstance(question, str) or not question.strip() or len(question) > 2000 or profile not in ('current', 'offline'):
                    raise ValueError('Unesite pitanje od 1 do 2000 znakova i ispravan režim.')
                localization.language_for(question, language)
                return self.reply(202, self.server.jobs.submit(dict(question=question, profile=profile, language=language)))
            if path == '/api/chat':
                result = chat_payload(data.get('question'), data.get('profile', 'current'), data.get('language', 'auto'))
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


def make_server(port=8767, static_dir=None):
    documents = documents_payload()
    server = WebServer(('127.0.0.1', port), partial(Handler, static_dir=static_dir))
    server.documents = documents
    server.jobs = JobManager(chat_payload)
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8767)
    args = parser.parse_args()
    server = make_server(args.port)
    print(f'Izvor je dostupan na http://localhost:{server.server_address[1]}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
