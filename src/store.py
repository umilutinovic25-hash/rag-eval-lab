"""Local SQLite state, independent from historical evaluation artifacts."""
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
import time


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('CREATE TABLE IF NOT EXISTS records (kind TEXT, id TEXT, data TEXT NOT NULL, updated REAL NOT NULL, PRIMARY KEY(kind,id))')

    @contextmanager
    def connect(self):
        with sqlite3.connect(self.path, timeout=10) as db:
            yield db

    def put(self, kind, key, data):
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO records VALUES (?,?,?,?)', (kind, key, json.dumps(data, ensure_ascii=False, allow_nan=False), time.time()))

    def get(self, kind, key):
        with self.connect() as db:
            row = db.execute('SELECT data FROM records WHERE kind=? AND id=?', (kind, key)).fetchone()
        return json.loads(row[0]) if row else None

    def all(self, kind):
        with self.connect() as db:
            rows = db.execute('SELECT data FROM records WHERE kind=? ORDER BY updated DESC', (kind,)).fetchall()
        return [json.loads(r[0]) for r in rows]

    def delete(self, kind, key):
        with self.connect() as db:
            db.execute('DELETE FROM records WHERE kind=? AND id=?', (kind, key))
