from fastapi import FastAPI, Request
from poisontrace.application.principals import Principal, principal_scope
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from contextlib import asynccontextmanager

from poisontrace.interfaces.http.routers import campaigns, credentials, runs, scenarios
from poisontrace.interfaces.http.routers import admin, auth
from poisontrace.application.accounts import AuthenticationError, UserSessionService


def create_app(backend, *, auth_service: UserSessionService):
    hosted = backend.web_config.profile == "hosted"
    @asynccontextmanager
    async def lifespan(app):
        with backend.executor_factory():
            yield

    app = FastAPI(lifespan=lifespan, docs_url=None if hosted else "/docs", redoc_url=None if hosted else "/redoc",
                  openapi_url=None if hosted else "/openapi.json")

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        if request.url.path.startswith(('/api/investigation-jobs', '/api/run-groups', '/api/runs', '/api/campaigns')):
            return JSONResponse({'detail': 'Invalid investigation submission'}, status_code=422)
        if request.url.path == "/api/auth/login":
            return JSONResponse({"detail": "Invalid sign-in request"}, status_code=422)
        if request.url.path.startswith("/api/admin/users/") and request.url.path.endswith("/passcode"):
            return JSONResponse({"detail": "Invalid passcode reset request"}, status_code=422)
        if request.url.path == "/api/admin/users" or request.url.path.startswith("/api/admin/users/"):
            return JSONResponse({"detail": "Invalid account-management request"}, status_code=422)
        return await request_validation_exception_handler(request, exc)
    from poisontrace.application.content_policy import ContentReadOnly
    from poisontrace.application.ports import ExecutionBusy

    @app.exception_handler(ExecutionBusy)
    async def execution_busy(request, exc):
        return JSONResponse({'detail': 'Execution storage is busy; retry the same intent'}, status_code=503, headers={'Retry-After': '1'})

    @app.middleware('http')
    async def bound_job_requests(request, call_next):
        if request.url.path.startswith(('/api/investigation-jobs', '/api/run-groups', '/api/runs', '/api/campaigns')) and request.method == 'POST':
            total = 0
            pieces = []
            async for piece in request.stream():
                total += len(piece)
                if total > 4096:
                    return JSONResponse({'detail': 'Investigation request is too large'}, status_code=413)
                pieces.append(piece)
            request._body = b''.join(pieces)
        return await call_next(request)

    @app.exception_handler(ContentReadOnly)
    async def content_read_only(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=403)

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
        with principal_scope(Principal(user.id, user.role)):
            return await call_next(request)
    from poisontrace.interfaces.http.routers import run_groups
    from poisontrace.interfaces.http.routers import jobs
    app.include_router(jobs.create_router(backend.jobs))
    app.include_router(run_groups.create_router(backend.groups, backend.jobs))
    app.include_router(runs.create_router(backend.runs))
    app.include_router(scenarios.create_router(backend.scenario_service))
    app.include_router(campaigns.create_router(backend.campaign_service, backend.jobs))
    app.include_router(credentials.create_router(backend.credentials))
    app.include_router(auth.create_router(auth_service, content_policy=backend.scenario_service.content_policy))
    app.include_router(admin.create_router(auth_service))
    from poisontrace.interfaces.http.security import install_security
    install_security(app, backend.web_config)
    return app
