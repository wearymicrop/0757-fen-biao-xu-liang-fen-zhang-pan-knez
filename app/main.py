import os

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles

from app.contract import STAGES
from app.errors import InputError, input_error_handler, validation_error_handler
from app.runs import router as runs_router
from app.settings import PROJECT, ROOT, RULE_VERSION, TITLE
from app.store import Archive
from app.web import router as web_router


def create_app(path=None):
    app = FastAPI(title=TITLE)
    app.state.archive = Archive(path or os.environ.get("DB_PATH", ROOT / "instance/archive.sqlite3"))
    app.add_exception_handler(InputError, input_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.mount("/static", StaticFiles(directory=ROOT / "app/static"), name="static")
    for _, _, _, router in STAGES:
        app.include_router(router)
    app.include_router(runs_router)
    app.include_router(web_router)

    @app.get("/api/health", tags=["服务状态"])
    def health():
        return {"status": "ok", "project": PROJECT, "rule_version": RULE_VERSION}

    return app


app = create_app()
