from fastapi import APIRouter, Header, HTTPException

from poisontrace.application.ports import ExecutionBusy
from poisontrace.application.principals import CredentialNotFound
from poisontrace.application.errors import ScenarioNotFound


def create_router(service):
    router = APIRouter(prefix='/api/investigation-jobs')

    @router.get('')
    def list_jobs():
        return service.list()

    @router.get('/{identifier}')
    def get_job(identifier: str):
        try:
            return service.get(identifier)
        except KeyError:
            raise HTTPException(404, 'job not found') from None

    @router.post('', status_code=202)
    def submit_job(payload: dict, idempotency_key: str = Header(default='')):
        try:
            return service.submit(idempotency_key, payload)
        except ExecutionBusy as exc:
            raise HTTPException(409, str(exc), headers={'Retry-After': '1'}) from None
        except CredentialNotFound:
            raise HTTPException(404, 'credential not found') from None
        except ScenarioNotFound:
            subject = 'scenario' if payload.get('workflow') == 'metadata-v1' else 'case'
            raise HTTPException(404, f'{subject} not found') from None
        except (ValueError, TypeError):
            raise HTTPException(400, 'Invalid investigation submission or conflicting intent') from None

    return router
