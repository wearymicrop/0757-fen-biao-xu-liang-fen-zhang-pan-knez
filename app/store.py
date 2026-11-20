import json
import sqlite3
from contextlib import closing
from pathlib import Path

from app.errors import InputError
from app.manifest import canonical


class _Table:
    def __init__(self, path, table):
        self.path = Path(path)
        self.table = table

    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection


class Runs(_Table):
    def __init__(self, path):
        super().__init__(path, "runs")

    def connect(self):
        connection = super().connect()
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


class Revisions(_Table):
    """修订表。publish_slot 只在已发布时填底稿号，配合唯一索引保证
    同一已签账单至多存在一条已发布修订。"""

    def __init__(self, path):
        super().__init__(path, "revisions")

    def connect(self):
        connection = super().connect()
        connection.execute("""CREATE TABLE IF NOT EXISTS revisions (
            digest TEXT PRIMARY KEY,
            base_run_id TEXT NOT NULL,
            publish_slot TEXT,
            created_at TEXT NOT NULL,
            payload TEXT NOT NULL
        )""")
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_revisions_published "
            "ON revisions(publish_slot) WHERE publish_slot IS NOT NULL")
        return connection

    def find(self, digest):
        with closing(self.connect()) as connection:
            row = connection.execute("SELECT payload FROM revisions WHERE digest = ?", (digest,)).fetchone()
        return json.loads(row[0]) if row else None

    def get(self, digest):
        result = self.find(digest)
        if result is None:
            raise InputError("REVISION_NOT_FOUND", "找不到该修订记录", 404)
        return result

    def list_for_base(self, base_run_id):
        with closing(self.connect()) as connection:
            rows = connection.execute(
                "SELECT payload FROM revisions WHERE base_run_id = ? ORDER BY created_at, digest",
                (base_run_id,)).fetchall()
        return [json.loads(row[0]) for row in rows]

    def save(self, record):
        with closing(self.connect()) as connection, connection:
            inserted = connection.execute(
                "INSERT INTO revisions(digest, base_run_id, publish_slot, created_at, payload) "
                "VALUES (?, ?, NULL, ?, ?) ON CONFLICT(digest) DO NOTHING",
                (record["id"], record["base_run_id"], record["created_at"], canonical(record))).rowcount
            payload = connection.execute(
                "SELECT payload FROM revisions WHERE digest = ?", (record["id"],)).fetchone()[0]
        return json.loads(payload), not inserted

    def mark_published(self, digest):
        with closing(self.connect()) as connection, connection:
            record_row = connection.execute(
                "SELECT base_run_id, payload FROM revisions WHERE digest = ?", (digest,)).fetchone()
            if record_row is None:
                raise InputError("REVISION_NOT_FOUND", "找不到该修订记录", 404)
            record = json.loads(record_row["payload"])
            if record["state"] == "published":
                return record
            try:
                cursor = connection.execute(
                    "UPDATE revisions SET publish_slot = ? WHERE digest = ? AND publish_slot IS NULL",
                    (record_row["base_run_id"], digest))
            except sqlite3.IntegrityError as error:
                raise InputError("REVISION_ALREADY_PUBLISHED",
                                 "该账单已有其他发布修订，唯一可发布版本不能被替换", 409) from error
            if cursor.rowcount == 0:
                raise InputError("REVISION_ALREADY_PUBLISHED",
                                 "该账单已有其他发布修订，唯一可发布版本不能被替换", 409)
            record["state"] = "published"
            record["published_at"] = _now()
            connection.execute("UPDATE revisions SET payload = ? WHERE digest = ?",
                               (canonical(record), digest))
        return record


def _now():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Archive:
    def __init__(self, path):
        self.path = Path(path)
        self.runs = Runs(path)
        self.revisions = Revisions(path)

    # 兼容既有调用方的薄封装。
    def connect(self):
        return self.runs.connect()

    def find(self, digest):
        return self.runs.find(digest)

    def get(self, digest):
        return self.runs.get(digest)

    def save(self, record):
        return self.runs.save(record)
