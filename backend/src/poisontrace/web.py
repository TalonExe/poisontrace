"""Local HTTP entrypoint: uvicorn poisontrace.web:app --reload."""

from poisontrace.bootstrap import build_web_backend, create_app

app = create_app(build_web_backend())
