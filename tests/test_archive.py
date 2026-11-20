import sqlite3
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from app.main import create_app
from app.runs import archive_run
from app.store import Archive


def test_concurrent_same_input_commits_once(tmp_path, clean_data):
    # TRAP-26：并发提交只建立一份不可变归档。
    path = tmp_path / "archive.sqlite3"
    store = Archive(path)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: archive_run(store, clean_data, None), range(8)))
    assert sum(not result["reused"] for result in results) == 1
    assert len({result["id"] for result in results}) == 1
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 1


def test_reopen_after_app_restart(tmp_path):
    path = tmp_path / "archive.sqlite3"
    with TestClient(create_app(path)) as first:
        saved = first.post("/api/runs", json={"sample": "clean"}).json()
    with TestClient(create_app(path)) as second:
        stored = second.get(f"/api/runs/{saved['id']}").json()
    assert stored == {key: value for key, value in saved.items() if key != "reused"}


def test_changed_source_separate_run(client, clean_data):
    one = client.post("/api/runs", json={"data": clean_data}).json()
    two = client.post("/api/runs", json={"sample": "dirty"}).json()
    assert one["manifest"]["input_sha256"] != two["manifest"]["input_sha256"]
    assert client.get(f"/api/runs/{one['id']}").json()["input"] == clean_data
