from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app.contract import HOME, STAGES
from app.errors import InputError
from app.manifest import sha256
from app.pipeline import calculate
from app.revisions import export_bundle
from app.samples import SAMPLE_NAMES, load_sample
from app.settings import ROOT, RULE_VERSION, TITLE

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=str(ROOT / "app/templates"))
templates.env.autoescape = True


def yuan(cents):
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}{cents // 100}.{cents % 100:02d}"


def signed_cents(cents):
    if cents is None:
        return "—"
    sign = "+" if cents > 0 else ""
    return f"{sign}{yuan(cents)}"


templates.env.filters["yuan"] = yuan
templates.env.filters["signed_cents"] = signed_cents


@router.get("/")
@router.get("/work/{stage}")
def workbench(request: Request, stage: str = HOME, sample: str = "clean"):
    titles = {name: caption for name, caption, _, _ in STAGES}
    if stage not in titles:
        raise InputError("UNKNOWN_STAGE", "找不到该业务页面", 404)
    data = load_sample(sample)
    result = calculate(data)
    return templates.TemplateResponse(request=request, name="workbench.html", context={
        "project": TITLE, "titles": titles, "stage": stage, "sample": sample,
        "samples": SAMPLE_NAMES, "result": result, "current": result[stage],
        "rule_version": RULE_VERSION, "input_ref": sha256(data)[:10],
    })


@router.get("/revisions/{revision_id}")
def revision_review(request: Request, revision_id: str):
    store = request.app.state.archive
    revision = store.revisions.get(revision_id)
    bundle = export_bundle(store, revision_id)
    return templates.TemplateResponse(request=request, name="revision.jinja", context={
        "project": TITLE, "revision": revision, "bundle": bundle,
        "old": bundle["old_signed_run"]["result"], "new": bundle["revised_run"]["result"],
        "rule_version": RULE_VERSION,
    })
