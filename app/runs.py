from time import perf_counter
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from app.errors import InputError
from app.manifest import identity, make_manifest
from app.pipeline import calculate, validate
from app.samples import load_sample
from app.settings import PROJECT

router = APIRouter(prefix="/api/runs", tags=["归档与证据"])


class Submission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sample: str | None = None
    data: dict[str, Any] | None = None


def archive_run(store, data, sample):
    validate(data)
    digest = identity(data, sample)
    existing = store.find(digest)
    if existing is not None:
        return {**existing, "reused": True}
    begin = perf_counter()
    result = calculate(data)
    elapsed_ms = round((perf_counter() - begin) * 1000, 3)
    record = {"id": digest, "manifest": make_manifest(data, sample, digest, elapsed_ms), "input": data, "result": result}
    stored, reused = store.save(record)
    return {**stored, "reused": reused}


@router.post("")
def create_run(body: Submission, request: Request):
    if (body.sample is None) == (body.data is None):
        raise InputError("CHOOSE_SOURCE", "请选择一个样例或提交数据")
    data = load_sample(body.sample) if body.sample is not None else body.data
    return archive_run(request.app.state.archive, data, body.sample)


@router.get("/{run_id}")
def get_run(run_id: str, request: Request):
    return request.app.state.archive.get(run_id)


@router.post("/{run_id}/rerun")
def rerun(run_id: str, request: Request):
    store = request.app.state.archive
    stored = store.get(run_id)
    return archive_run(store, stored["input"], stored["manifest"]["sample"])


@router.get("/{run_id}/export")
def export_run(run_id: str, request: Request):
    return JSONResponse(request.app.state.archive.get(run_id), headers={
        "Content-Disposition": f'attachment; filename="{PROJECT}-{run_id[:12]}.json"'
    })
