from fastapi import APIRouter
from app.samples import load_sample


def stage_router(name, caption):
    router = APIRouter(prefix=f"/api/{name}", tags=[caption])

    @router.get("/{sample}", name=name)
    def inspect(sample: str):
        from app.pipeline import calculate

        return calculate(load_sample(sample), until=name)[name]

    return router
