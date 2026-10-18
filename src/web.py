"""Local, same-origin web interface. Start with: python -m src.web."""
import argparse
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import threading
import time
from urllib.parse import unquote, urlsplit
import urllib.request

from . import config, embeddings, llm, rag
from .chunking import build_chunks
from .corpus import load_corpus

ROOT = Path(__file__).resolve().parents[1]
BASE_CONFIG = config.snapshot()
PIPELINE_LOCK = threading.RLock()
SAVED_EVALUATION = ROOT / 'evidence/improvements/final-manifest.json'


@contextmanager
def profile_scope(profile):
    """The CLI pipeline uses globals; serialize requests and always restore them."""
    if profile not in ('current', 'offline'):
        raise ValueError('Nepoznat režim rada.')
    with PIPELINE_LOCK:
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


def chat_payload(question, profile='current'):
    if not isinstance(question, str) or not question.strip() or len(question) > 2000:
        raise ValueError('Unesite pitanje od 1 do 2000 znakova.')
    started = time.perf_counter()
    with profile_scope(profile):
        chunks = build_chunks(load_corpus())
        by_id = {c.chunk_id: c for c in chunks}
        result = rag.build_grounded_answer(question.strip(), chunks)
        return dict(answer=result.answer, refused=result.refused,
                    citations=[asdict(by_id[c]) for c in result.citations],
                    retrieved=[dict(asdict(r.chunk), score=r.score) for r in result.retrieved],
                    trace=result.trace, fallback=result.generation_fallback_reason,
                    question=question.strip(), profile=profile,
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
        if path == '/api/status':
            online = False
            models = []
            try:
                with urllib.request.urlopen('http://127.0.0.1:11434/api/tags', timeout=0.8) as response:
                    models = [m['name'] for m in json.load(response)['models']]
                    online = True
            except (OSError, ValueError, KeyError, TypeError):
                pass
            return self.reply(200, dict(ollama=online, models=models,
                                      required_models=['bge-m3', 'qwen2.5:7b', 'gemma3:4b'],
                                      documents=10, current_documents=9))
        if path == '/api/documents':
            return self.reply(200, {'documents': documents_payload()})
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
        if path not in ('/api/chat', '/api/evaluations/run'):
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
            if path == '/api/chat':
                result = chat_payload(data.get('question'), data.get('profile', 'current'))
            else:
                from .experiment_runner import execute
                with profile_scope('current'):
                    result = evaluation_payload(execute('replay'), 'replayed')
            return self.reply(200, result)
        except (ValueError, UnicodeDecodeError) as error:
            return self.reply(400, {'error': str(error)})
        except (embeddings.EmbeddingError, llm.LLMError) as error:
            return self.reply(503, {'error': 'Lokalni model nije dostupan za ovo pitanje. Pokrenite Ollama ili izaberite režim Bez modela.', 'detail': str(error)})
        except Exception:
            return self.reply(500, {'error': 'Provera nije završena. Pokušajte ponovo ili koristite režim Bez modela.'})


def make_server(port=8767, static_dir=None):
    return WebServer(('127.0.0.1', port), partial(Handler, static_dir=static_dir))


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
