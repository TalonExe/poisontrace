from typing import Any

from fastapi import APIRouter, HTTPException


def create_router(service):
    router = APIRouter(prefix="/api/scenarios")

    @router.get("")
    def list_scenarios():
        return service.list()

    @router.get("/{scenario_id}")
    def get_scenario(scenario_id: str):
        try:
            return service.get(scenario_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="scenario not found") from exc

    @router.post("", status_code=201)
    def create_scenario(payload: dict[str, Any]):
        try:
            return service.create(payload)
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.put("/{scenario_id}")
    def update_scenario(scenario_id: str, payload: dict[str, Any]):
        try:
            return service.update(scenario_id, payload)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="scenario not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.delete("/{scenario_id}")
    def delete_scenario(scenario_id: str):
        try:
            service.delete(scenario_id)
            return {"scenario_id": scenario_id, "deleted": True}
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="scenario not found") from exc

    return router
