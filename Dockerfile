# syntax=docker/dockerfile:1
FROM docker.io/library/node:26.12.0-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/index.html frontend/vite.config.js ./
COPY frontend/src ./src
RUN npm run build

FROM docker.io/library/python:3.12.12-slim-bookworm AS wheels
WORKDIR /build
COPY requirements-runtime.lock pyproject.toml ./
RUN python -m pip install --no-cache-dir setuptools==80.9.0 wheel==0.45.1
COPY backend/src ./backend/src
RUN python -m pip wheel --no-cache-dir --wheel-dir /wheels -r requirements-runtime.lock && \
    python -m pip wheel --no-deps --no-build-isolation --wheel-dir /wheels .

FROM docker.io/library/python:3.12.12-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    POISONTRACE_DATA_ROOT=/data POISONTRACE_FRONTEND_ROOT=/opt/poisontrace/frontend \
    POISONTRACE_PROFILE=local PORT=8000 POISONTRACE_BIND=0.0.0.0
COPY --from=wheels /wheels /wheels
COPY requirements-runtime.lock /opt/poisontrace/requirements-runtime.lock
RUN python -m pip install --no-cache-dir --no-index --find-links=/wheels \
      -r /opt/poisontrace/requirements-runtime.lock poisontrace==0.1.0 && \
    python -m pip check && rm -rf /wheels && \
    groupadd --gid 10001 poisontrace && useradd --uid 10001 --gid 10001 --no-create-home poisontrace && \
    mkdir -p /data && chown 10001:10001 /data
COPY --from=frontend /build/dist /opt/poisontrace/frontend
USER 10001:10001
WORKDIR /opt/poisontrace
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8000')+'/health/ready',timeout=2)"
ENTRYPOINT ["python", "-m", "poisontrace.production"]
CMD ["serve"]
