from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.revisions import RevisionRequest, create_revision, export_bundle, publish_revision
from app.settings import PROJECT

router = APIRouter(prefix="/api/revisions", tags=["账单修订"])


@router.post("")
def submit_revision(body: RevisionRequest, request: Request):
    record, reused = create_revision(request.app.state.archive, body.base_run_id, body)
    return {**record, "reused": reused}


@router.get("/{revision_id}")
def get_revision(revision_id: str, request: Request):
    return request.app.state.archive.revisions.get(revision_id)


@router.get("/base/{base_run_id}")
def list_base_revisions(base_run_id: str, request: Request):
    return {"base_run_id": base_run_id,
            "revisions": request.app.state.archive.revisions.list_for_base(base_run_id)}


@router.post("/{revision_id}/publish")
def publish(revision_id: str, request: Request):
    return publish_revision(request.app.state.archive, revision_id)


@router.get("/{revision_id}/export")
def export_revision(revision_id: str, request: Request):
    bundle = export_bundle(request.app.state.archive, revision_id)
    return JSONResponse(bundle, headers={
        "Content-Disposition": f'attachment; filename="{PROJECT}-revision-{revision_id[:12]}.json"'
    })
