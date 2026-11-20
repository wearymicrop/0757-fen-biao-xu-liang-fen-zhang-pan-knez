from app.contract import STAGES


def test_independent_stage_endpoints(client, clean):
    for stage, _, _, _ in STAGES:
        response = client.get(f"/api/{stage}/clean")
        assert response.status_code == 200
        assert response.json() == clean[stage]


def test_immutable_evidence_download(client, dirty_data):
    record = client.post("/api/runs", json={"data": dirty_data}).json()
    identifier = record["id"]
    rerun = client.post(f"/api/runs/{identifier}/rerun").json()
    assert rerun["reused"] and rerun["manifest"] == record["manifest"]
    attachment = client.get(f"/api/runs/{identifier}/export")
    assert attachment.headers["content-disposition"].startswith("attachment;")
    assert attachment.json()["input"] == dirty_data
    assert attachment.json()["result"] == record["result"]


def test_error_paths(client):
    assert client.post("/api/runs", json={}).json()["code"] == "CHOOSE_SOURCE"
    assert client.post("/api/runs", json={"data": {}}).json()["code"] == "INPUT_TABLES"
    assert client.get("/api/runs/unknown").status_code == 404
    assert client.get("/work/unknown").status_code == 404


def test_workbench_and_navigation(client):
    for stage, caption, _, _ in STAGES:
        response = client.get(f"/work/{stage}?sample=dirty")
        assert response.status_code == 200
        assert f'aria-current="page">{caption}' in response.text
    assert client.get("/?sample=unknown").status_code == 404
