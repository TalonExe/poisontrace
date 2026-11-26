from ipaddress import ip_address, ip_network
from urllib.parse import urlsplit

from fastapi.responses import JSONResponse


def install_security(app, config):
    config.validate_http()
    hosted = config.profile == "hosted"
    authority = urlsplit(config.public_origin).netloc
    networks = tuple(ip_network(value) for value in config.trusted_proxy_cidrs)

    @app.middleware("http")
    async def protect_request(request, call_next):
        path = request.url.path
        request.state.login_peer = request.client.host if request.client else "unknown"
        response = None
        if hosted and not path.startswith("/health/"):
            scheme = request.scope["scheme"]
            try:
                peer = ip_address(request.state.login_peer)
                trusted = any(peer in network for network in networks)
            except ValueError:
                trusted = False
            if trusted:
                scheme = request.headers.get("x-forwarded-proto", "")
                forwarded = request.headers.get("x-forwarded-for", "")
                if len(request.headers.getlist("x-forwarded-proto")) != 1 or len(request.headers.getlist("x-forwarded-for")) != 1:
                    response = JSONResponse({"detail": "Invalid proxy headers"}, status_code=400)
                try:
                    request.state.login_peer = str(ip_address(forwarded))
                except ValueError:
                    response = JSONResponse({"detail": "Invalid proxy headers"}, status_code=400)
            if scheme != "https" or request.headers.getlist("host") != [authority]:
                response = JSONResponse({"detail": "HTTPS and the configured host are required"}, status_code=400)
            if response is None and trusted:
                request.scope["scheme"] = "https"
            if path.rstrip("/") in {"/docs", "/redoc", "/openapi.json"} or path.startswith("/docs/"):
                response = JSONResponse({"detail": "Not found"}, status_code=404)
            if response is None and request.method not in {"GET", "HEAD", "OPTIONS"}:
                origins = request.headers.getlist("origin")
                if origins != [config.public_origin] or request.headers.get("sec-fetch-site") == "cross-site":
                    response = JSONResponse({"detail": "A same-origin request is required"}, status_code=403)
        if response is None:
            response = await call_next(request)
        if path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response
