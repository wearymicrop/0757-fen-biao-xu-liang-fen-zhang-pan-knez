"""账单修订：迟到读数补录、归属更正、唯一发布与证据追回。"""
import copy
import sqlite3
from concurrent.futures import ThreadPoolExecutor

from app.revisions import Correction, create_revision, revision_identity
from app.samples import load_sample

LATE = {"gateway": "G-B", "meter": "M-001", "at": "2026-11-20T08:31:00+08:00",
        "value": "42", "unit": "kW"}
MAPPINGS = [
    {"meter": "M-001", "account": "厂房丁", "version": "v3",
     "start": "2026-11-20T08:00:00+08:00", "end": "2026-11-20T09:00:00+08:00"},
    {"meter": "M-001", "account": "厂房丁", "version": "v2",
     "start": "2026-11-20T09:00:00+08:00", "end": "2026-11-20T10:00:00+08:00"},
]


def _base_with_late_gap():
    """抽走 08:31 读数后，08:30 窗缺样，共同峰停在 08:45。"""
    data = load_sample("clean")
    data["readings"] = [row for row in data["readings"]
                        if not (row["meter"] == "M-001" and row["at"] == LATE["at"])]
    return data


def _signed_base(client):
    return client.post("/api/runs", json={"data": _base_with_late_gap()}).json()


def _correction(base_id, **overrides):
    body = {"base_run_id": base_id, "late_readings": [LATE], "mapping_replacements": MAPPINGS,
            "note": "月末补录迟到读数并更正归属"}
    body.update(overrides)
    return body


def test_late_reading_moves_peak_and_recomputes_amounts(client):
    base = _signed_base(client)
    assert base["result"]["peak"]["peak"]["label"] == "11/20 08:45"
    revision = client.post("/api/revisions", json=_correction(base["id"])).json()
    comparison = revision["comparison"]
    assert comparison["peak"]["moved"] is True
    assert comparison["peak"]["before"]["label"] == "11/20 08:45"
    assert comparison["peak"]["after"]["label"] == "11/20 08:30"
    # 归属更正使厂房甲退场、厂房丁进场，差额方向与金额一致。
    by_account = {row["account"]: row for row in comparison["accounts"]}
    assert by_account["厂房甲"]["after_cents"] is None and by_account["厂房甲"]["delta_cents"] < 0
    assert by_account["厂房丁"]["before_cents"] is None and by_account["厂房丁"]["after_cents"] > 0
    assert comparison["total"]["after_cents"] == 244260
    assert comparison["unallocated"]["after_w_sum"] == 39001
    assert revision["publishable"] is True and revision["state"] == "draft"
    # 旧版结果原样保留在修订记录引用的底稿里。
    old = client.get(f"/api/runs/{revision['base_run_id']}").json()
    assert old["result"]["peak"]["peak"]["label"] == "11/20 08:45"


def test_duplicate_submission_returns_same_revision(client):
    base = _signed_base(client)
    body = _correction(base["id"])
    first = client.post("/api/revisions", json=body).json()
    second = client.post("/api/revisions", json=body).json()
    assert first["id"] == second["id"] and second["reused"] is True
    assert len(client.get(f"/api/revisions/base/{base['id']}").json()["revisions"]) == 1


def test_concurrent_identical_correction_commits_once(tmp_path, client):
    base = _signed_base(client)
    body = _correction(base["id"])
    store = client.app.state.archive
    correction = Correction(late_readings=body["late_readings"],
                            mapping_replacements=body["mapping_replacements"], note=body["note"])
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(
            lambda _: create_revision(store, base["id"], correction)[0], range(8)))
    assert len({item["id"] for item in results}) == 1
    with sqlite3.connect(store.path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM revisions").fetchone()[0] == 1


def test_publish_is_idempotent_and_unique_per_base(client):
    base = _signed_base(client)
    revision = client.post("/api/revisions", json=_correction(base["id"])).json()
    published = client.post(f"/api/revisions/{revision['id']}/publish").json()
    assert published["state"] == "published" and published["published_at"]
    again = client.post(f"/api/revisions/{revision['id']}/publish").json()
    assert again["id"] == revision["id"] and again["state"] == "published"
    # 同一底稿的另一条修订不能再抢占唯一发布位。
    competitor = client.post("/api/revisions", json=_correction(base["id"], note="另一处修订")).json()
    response = client.post(f"/api/revisions/{competitor['id']}/publish")
    assert response.status_code == 409 and response.json()["code"] == "REVISION_ALREADY_PUBLISHED"
    assert client.get(f"/api/revisions/{competitor['id']}").json()["state"] == "draft"


def test_unbalanced_revision_cannot_publish_and_retry_adds_nothing(client):
    base = _signed_base(client)
    conflicting = {**LATE, "value": "999"}  # 与底稿已存在的同刻读数异值 -> 隔离、窗口仍缺样
    revision = client.post(
        "/api/revisions", json={"base_run_id": base["id"], "late_readings": [conflicting]}).json()
    assert revision["publishable"] is False
    assert revision["blockers"] and revision["state"] == "draft"
    first = client.post(f"/api/revisions/{revision['id']}/publish")
    second = client.post(f"/api/revisions/{revision['id']}/publish")
    assert first.status_code == second.status_code == 422
    assert first.json()["code"] == second.json()["code"] == "REVISION_NOT_PUBLISHABLE"
    assert client.get(f"/api/revisions/{revision['id']}").json()["state"] == "draft"


def test_missing_archive_blocks_creation_and_publish(client):
    base = _signed_base(client)
    revision = client.post("/api/revisions", json=_correction(base["id"])).json()
    with sqlite3.connect(client.app.state.archive.path) as connection:
        connection.execute("DELETE FROM runs WHERE digest=?", (base["id"],))
    # 底稿丢失时连新的更正提交也不能建立。
    response = client.post("/api/revisions", json=_correction(base["id"]))
    assert response.status_code == 409 and response.json()["code"] == "REVISION_BASE_MISSING"
    # 已满足过发布条件的修订在旧据丢失后同样被拦截。
    blocked = client.post(f"/api/revisions/{revision['id']}/publish")
    assert blocked.status_code == 409 and blocked.json()["code"] == "REVISION_BASE_MISSING"
    assert client.get(f"/api/revisions/{revision['id']}").json()["state"] == "draft"


def test_revision_bundle_recovers_old_version_and_sources(client):
    base = _signed_base(client)
    revision = client.post("/api/revisions", json=_correction(base["id"])).json()
    response = client.get(f"/api/revisions/{revision['id']}/export")
    assert response.headers["content-disposition"].startswith("attachment;")
    bundle = response.json()
    assert bundle["schema"] == "bill-revision"
    assert bundle["old_signed_run"]["id"] == base["id"]
    assert bundle["old_signed_run"]["input"] == base["input"]
    assert bundle["revised_run"]["id"] == revision["new_run_id"]
    assert bundle["evidence"]["late_readings"] == [LATE]
    # 被替换的旧映射行原样留痕，且替换整表覆盖。
    assert {row["meter"] for row in bundle["evidence"]["replaced_mappings"]} == {"M-001"}
    assert len(bundle["evidence"]["replaced_mappings"]) == 2
    assert bundle["evidence"]["old_input_sha256"] == base["manifest"]["input_sha256"]
    # 旧版单独导出链接继续可用，未被修订替换。
    assert client.get(f"/api/runs/{base['id']}/export").status_code == 200


def test_correction_validation(client):
    base = _signed_base(client)
    assert client.post("/api/revisions", json={"base_run_id": base["id"]}).json()["code"] == "REVISION_EMPTY"
    bad_row = client.post(
        "/api/revisions", json={"base_run_id": base["id"], "late_readings": [{"meter": "X"}]}).json()
    assert bad_row["code"] == "REVISION_BAD_ROW"
    missing = client.post(
        "/api/revisions", json={"base_run_id": "ghost", "late_readings": [LATE]})
    assert missing.status_code == 409 and missing.json()["code"] == "REVISION_BASE_MISSING"
    assert client.get("/api/revisions/ghost").status_code == 404


def test_held_base_cannot_start_revision(client, clean_data):
    for row in clean_data["readings"]:
        if row["meter"] == "M-003":
            row.update(value="200", unit="kW")
    held = client.post("/api/runs", json={"data": clean_data}).json()
    assert held["result"]["billing"]["state"] == "held"
    response = client.post(
        "/api/revisions", json={"base_run_id": held["id"], "late_readings": [LATE]})
    assert response.status_code == 422 and response.json()["code"] == "REVISION_BASE_NOT_SIGNED"


def test_revision_review_page_shows_diff_and_basis(client):
    base = _signed_base(client)
    revision = client.post("/api/revisions", json=_correction(base["id"])).json()
    page = client.get(f"/revisions/{revision['id']}")
    assert page.status_code == 200
    for fragment in ("新旧峰窗对照", "住户金额差额", "采用依据", "发布闸门",
                     "峰窗已移走", "下载修订证据包", "被替换的旧映射行"):
        assert fragment in page.text


def test_revision_identity_is_content_addressed():
    correction = {"late_readings": [LATE], "mapping_replacements": MAPPINGS, "note": "n"}
    one = revision_identity("base-a", correction)
    assert one == revision_identity("base-a", copy.deepcopy(correction))
    assert one != revision_identity("base-b", copy.deepcopy(correction))
