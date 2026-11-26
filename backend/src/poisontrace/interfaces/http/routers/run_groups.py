from poisontrace.application.ports import ExecutionBusy
from poisontrace.application.principals import CredentialNotFound
from fastapi import APIRouter, Header, HTTPException
from poisontrace.application.errors import ScenarioNotFound


def create_router(service, jobs):
    router = APIRouter(prefix='/api/run-groups')

    def translate(action):
        try:
            return action()
        except ExecutionBusy as exc:
            raise HTTPException(409, str(exc), headers={'Retry-After': '1'}) from None
        except CredentialNotFound as exc:
            raise HTTPException(status_code=404, detail="credential not found") from exc
        except (KeyError, ScenarioNotFound) as error:
            raise HTTPException(status_code=404, detail='group or case not found') from error
        except (ValueError, TypeError) as error:
            raise HTTPException(status_code=400, detail='Invalid group submission or conflicting intent') from error

    @router.get('')
    def list_groups():
        return service.list()

    @router.post('', status_code=202)
    def create_group(payload: dict, idempotency_key: str = Header(default='')):
        return translate(lambda: jobs.submit_group(idempotency_key, payload))

    @router.get('/{identifier}')
    def get_group(identifier: str):
        return translate(lambda: service.get(identifier))

    @router.post('/{identifier}/execute', status_code=202)
    def execute_group(identifier: str, payload: dict, idempotency_key: str = Header(default='')):
        return translate(lambda: jobs.submit_group(idempotency_key, payload, identifier))

    return router
