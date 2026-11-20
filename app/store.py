import json
import sqlite3
from contextlib import closing
from pathlib import Path

from app.errors import InputError
from app.manifest import canonical


class Archive:
    def __init__(self, path):
        self.path = Path(path)

    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=10)
        connection.execute("""CREATE TABLE IF NOT EXISTS runs (
            digest TEXT PRIMARY KEY, payload TEXT NOT NULL
        )""")
        return connection

    def find(self, digest):
        with closing(self.connect()) as connection:
            row = connection.execute("SELECT payload FROM runs WHERE digest = ?", (digest,)).fetchone()
        return json.loads(row[0]) if row else None

    def get(self, digest):
        result = self.find(digest)
        if result is None:
            raise InputError("RUN_NOT_FOUND", "找不到该归档", 404)
        return result

    def save(self, record):
        with closing(self.connect()) as connection, connection:
            inserted = connection.execute(
                "INSERT INTO runs VALUES (?, ?) ON CONFLICT(digest) DO NOTHING",
                (record["id"], canonical(record)),
            ).rowcount
            payload = connection.execute("SELECT payload FROM runs WHERE digest = ?", (record["id"],)).fetchone()[0]
        return json.loads(payload), not inserted
