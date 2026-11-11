from typing import Any

from fastapi import APIRouter, HTTPException
from poisontrace.application.errors import ScenarioNotFound
from poisontrace.application.runs import RunApplicationService


def create_router(service: RunApplicationService):
    router = APIRouter(prefix="/api/runs")

    @router.get("")
    def list_runs():
        return service.list()

    @router.get("/{run_id}")
    def get_run(run_id: int):
        try:
            return service.get(run_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="run not found") from exc

    @router.post("")
    def create_run(payload: dict[str, Any]):
        try:
            return service.create(payload)
        except ScenarioNotFound as exc:
            raise HTTPException(status_code=404, detail="scenario not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return router
