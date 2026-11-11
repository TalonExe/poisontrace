from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from poisontrace.interfaces.http.routers import campaigns, credentials, runs, scenarios
from poisontrace.interfaces.http.routers import admin, auth
from poisontrace.application.accounts import AuthenticationError, UserSessionService


def create_app(backend, *, auth_service: UserSessionService):
    app = FastAPI()

    @app.middleware("http")
    async def enforce_role_boundaries(request: Request, call_next):
        if request.url.path.startswith("/api/auth") or request.url.path == "/docs" or request.url.path.startswith("/openapi"):
            return await call_next(request)
        if not request.url.path.startswith("/api/"):
            return await call_next(request)
        try:
            user = auth_service.current_user(request.cookies.get("poisontrace_session"))
        except AuthenticationError:
            return JSONResponse({"detail": "Authentication required"}, status_code=401)
        if request.url.path.startswith("/api/admin"):
            if user.role != "superadmin":
                return JSONResponse({"detail": "Forbidden"}, status_code=403)
            return await call_next(request)
        if user.role != "analyst":
            return JSONResponse({"detail": "Forbidden"}, status_code=403)
        return await call_next(request)
    app.include_router(runs.create_router(backend.runs))
    app.include_router(scenarios.create_router(backend.scenario_service))
    app.include_router(campaigns.create_router(backend.campaign_service))
    app.include_router(credentials.create_router(backend.credentials))
    app.include_router(auth.create_router(auth_service))
    app.include_router(admin.create_router(auth_service))
    return app
