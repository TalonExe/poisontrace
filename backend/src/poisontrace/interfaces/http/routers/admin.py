from fastapi import APIRouter, HTTPException, Request

from poisontrace.application.accounts import AuthenticationError, UserSessionService


def create_router(service: UserSessionService):
    router = APIRouter(prefix="/api/admin")

    def require_superadmin(request: Request):
        try:
            user = service.current_user(request.cookies.get("poisontrace_session"))
        except AuthenticationError as exc:
            raise HTTPException(status_code=401, detail="Authentication required") from exc
        if user.role != "superadmin":
            raise HTTPException(status_code=403, detail="Forbidden")

    @router.get("/users")
    def list_users(request: Request, search: str = ""):
        require_superadmin(request)
        return [user.public_dict() for user in service.list_users(search)]

    @router.post("/users", status_code=201)
    def create_user(payload: dict[str, str], request: Request):
        require_superadmin(request)
        try:
            return service.create_analyst(payload.get("username", ""), payload.get("display_name", ""), payload.get("passcode", "")).public_dict()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.patch("/users/{user_id}")
    def update_user(user_id: int, payload: dict[str, str], request: Request):
        require_superadmin(request)
        try:
            return service.update_user(user_id, display_name=payload.get("display_name"), role=payload.get("role"), status=payload.get("status")).public_dict()
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="User not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return router
