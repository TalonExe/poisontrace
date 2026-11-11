from typing import Any

from fastapi import APIRouter, HTTPException

from poisontrace.application.campaigns import CampaignApplicationService


def create_router(service: CampaignApplicationService):
    router = APIRouter(prefix="/api/campaigns")

    @router.post("", status_code=201)
    def create_campaign(payload: dict[str, Any]):
        try:
            return service.create(payload)
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.get("")
    def list_campaigns():
        return service.list()

    @router.get("/{campaign_id}")
    def get_campaign(campaign_id: str):
        try:
            return service.get(campaign_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="campaign not found") from exc

    @router.post("/{campaign_id}/execute")
    def execute_campaign(campaign_id: str):
        try:
            return service.execute(campaign_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="campaign not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.post("/{campaign_id}/scenarios/{ordinal}/rerun")
    def rerun_campaign_scenario(campaign_id: str, ordinal: int):
        try:
            return service.rerun(campaign_id, ordinal)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="campaign scenario not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return router
