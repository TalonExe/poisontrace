from fastapi import APIRouter, HTTPException
from poisontrace.application.errors import ScenarioNotFound


def create_router(service):
    router = APIRouter(prefix='/api/run-groups')

    def translate(action):
        try:
            return action()
        except (KeyError, ScenarioNotFound) as error:
            raise HTTPException(status_code=404, detail='group or case not found') from error
        except (ValueError, TypeError) as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    @router.get('')
    def list_groups():
        return service.list()

    @router.post('')
    def create_group(payload: dict):
        return translate(lambda: service.create(payload))

    @router.get('/{identifier}')
    def get_group(identifier: str):
        return translate(lambda: service.get(identifier))

    @router.post('/{identifier}/execute')
    def execute_group(identifier: str, payload: dict):
        return translate(lambda: service.execute(identifier,payload))

    return router
