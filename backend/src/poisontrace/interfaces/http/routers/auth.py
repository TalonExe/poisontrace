from fastapi import APIRouter, Cookie, HTTPException, Response

from poisontrace.application.accounts import AuthenticationError, UserSessionService


def create_router(service: UserSessionService):
    router = APIRouter(prefix="/api/auth")

    @router.post("/login")
    def login(payload: dict[str, str], response: Response):
        try:
            user, token = service.authenticate(payload.get("username", ""), payload.get("passcode", ""))
        except AuthenticationError as exc:
            raise HTTPException(status_code=401, detail="Invalid credentials") from exc
        response.set_cookie("poisontrace_session", token, httponly=True, samesite="lax")
        return {"user": user.public_dict(), "redirect": "/admin/users" if user.role == "superadmin" else "/sessions"}

    @router.get("/session")
    def session(poisontrace_session: str | None = Cookie(default=None)):
        try:
            return {"user": service.current_user(poisontrace_session).public_dict()}
        except AuthenticationError as exc:
            raise HTTPException(status_code=401, detail="Authentication required") from exc

    @router.post("/logout", status_code=204)
    def logout(response: Response, poisontrace_session: str | None = Cookie(default=None)):
        service.logout(poisontrace_session)
        response.delete_cookie("poisontrace_session")

    return router
