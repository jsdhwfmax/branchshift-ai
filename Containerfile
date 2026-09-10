# syntax=docker/dockerfile:1
FROM node:24-bookworm-slim AS web
WORKDIR /build
RUN npm install --global pnpm@11.19.0
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/package.json
RUN pnpm install --frozen-lockfile
COPY apps/web ./apps/web
ENV VITE_API_BASE=""
RUN pnpm web:build

FROM python:3.13-slim-bookworm AS runtime
WORKDIR /opt/branchshift
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    BRANCHSHIFT_MODE=mock \
    DATABASE_URL=sqlite:////data/runs.db \
    MAX_CONCURRENT_RUNS=1 \
    RUN_TIMEOUT_SECONDS=900

COPY services/api/pyproject.toml ./services/api/pyproject.toml
COPY services/api/app ./services/api/app
RUN python -m pip install --no-cache-dir './services/api[contree]' \
    && groupadd --gid 10001 branchshift \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin branchshift \
    && mkdir -p /data \
    && chown 10001:10001 /data
COPY --from=web /build/apps/web/dist ./apps/web/dist

# /data must be backed by explicitly selected, verified persistent storage.
# An image directory or anonymous container volume is not a durability guarantee.
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api', timeout=3).read()"]
CMD ["python", "-m", "uvicorn", "app.main:app", "--app-dir", "/opt/branchshift/services/api", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
