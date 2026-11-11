from typing import Any

from fastapi import APIRouter, HTTPException

from poisontrace.application.credentials import CredentialApplicationService


def create_router(service: CredentialApplicationService):
    router = APIRouter(prefix="/api/credentials")

    @router.get("")
    def list_credentials():
        try:
            return service.list()
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @router.post("")
    def save_credential(payload: dict[str, Any]):
        try:
            return service.save(payload)
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.put("/{credential_id}")
    def replace_credential(credential_id: str, payload: dict[str, Any]):
        try:
            return service.replace(credential_id, payload)
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.post("/{credential_id}/test")
    def test_credential(credential_id: str):
        try:
            return service.test(credential_id)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="credential not found") from exc

    @router.delete("/{credential_id}")
    def revoke_credential(credential_id: str):
        try:
            return service.revoke(credential_id)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="credential not found") from exc

    return router
