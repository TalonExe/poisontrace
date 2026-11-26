from poisontrace.application.principals import CredentialNotFound
from typing import Any

from fastapi import APIRouter, Header, HTTPException

from poisontrace.application.campaigns import CampaignApplicationService
from poisontrace.application.ports import ExecutionBusy


def create_router(service: CampaignApplicationService, jobs):
    router = APIRouter(prefix="/api/campaigns")

    @router.post("", status_code=201)
    def create_campaign(payload: dict[str, Any]):
        try:
            return service.create(payload)
        except CredentialNotFound as exc:
            raise HTTPException(status_code=404, detail="credential not found") from exc
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

    @router.post("/{campaign_id}/execute", status_code=202)
    def execute_campaign(campaign_id: str, idempotency_key: str = Header(default=''), payload: dict | None = None):
        try:
            payload = payload or {}
            acknowledged = payload.get('excluded_files', [])
            if set(payload) - {'excluded_files'} or not isinstance(acknowledged, list) or any(not isinstance(name, str) for name in acknowledged):
                raise ValueError('invalid campaign execution request')
            return jobs.submit_campaign(idempotency_key, campaign_id, acknowledged=acknowledged)
        except ExecutionBusy as exc:
            raise HTTPException(409, str(exc), headers={'Retry-After': '1'}) from None
        except CredentialNotFound as exc:
            raise HTTPException(status_code=404, detail="credential not found") from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="campaign not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.post("/{campaign_id}/scenarios/{ordinal}/rerun", status_code=202)
    def rerun_campaign_scenario(campaign_id: str, ordinal: int, idempotency_key: str = Header(default='')):
        try:
            return jobs.submit_campaign(idempotency_key, campaign_id, ordinal)
        except ExecutionBusy as exc:
            raise HTTPException(409, str(exc), headers={'Retry-After': '1'}) from None
        except CredentialNotFound as exc:
            raise HTTPException(status_code=404, detail="credential not found") from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="campaign scenario not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return router
