from poisontrace.application.content_policy import ContentPolicy

from fastapi import APIRouter, Cookie, HTTPException, Response, Request
from pydantic import BaseModel, Field

from poisontrace.application.accounts import AuthenticationError, UserSessionService, LoginThrottled


class LoginRequest(BaseModel):
    username: str = Field(default="", max_length=254)
    passcode: str = Field(default="", max_length=1024)


def create_router(service: UserSessionService, *, content_policy: ContentPolicy = ContentPolicy()):
    router = APIRouter(prefix="/api/auth")

    def public_user(user):
        return {**user.public_dict(), "content_read_only": content_policy.read_only}

    @router.post("/login")
    def login(payload: LoginRequest, response: Response, request: Request):
        try:
            user, token = service.authenticate(payload.username, payload.passcode,
                client_address=request.state.login_peer if content_policy.read_only else None)
        except LoginThrottled as exc:
            raise HTTPException(status_code=429, detail=str(exc), headers={"Retry-After": str(exc.retry_after)}) from exc
        except AuthenticationError as exc:
            raise HTTPException(status_code=401, detail="Invalid credentials") from exc
        response.set_cookie("poisontrace_session", token, httponly=True, secure=content_policy.read_only,
                            samesite="lax", max_age=service.session_seconds)
        return {"user": public_user(user), "redirect": "/admin/users" if user.role == "superadmin" else "/activity"}

    @router.get("/session")
    def session(poisontrace_session: str | None = Cookie(default=None)):
        try:
            return {"user": public_user(service.current_user(poisontrace_session))}
        except AuthenticationError as exc:
            raise HTTPException(status_code=401, detail="Authentication required") from exc

    @router.post("/logout", status_code=204)
    def logout(response: Response, poisontrace_session: str | None = Cookie(default=None)):
        service.logout(poisontrace_session)
        response.delete_cookie("poisontrace_session", secure=content_policy.read_only, httponly=True, samesite="lax")

    return router
