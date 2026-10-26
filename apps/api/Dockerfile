FROM python:3.12-slim AS builder
WORKDIR /app
ENV UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
COPY --from=ghcr.io/astral-sh/uv:0.11.19@sha256:b46b03ddfcfbf8f547af7e9eaefdf8a39c8cebcba7c98858d3162bd28cf536f6 /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
COPY backend/pyproject.toml ./backend/pyproject.toml
COPY apps/api/pyproject.toml ./apps/api/pyproject.toml
COPY backend/src ./backend/src
COPY apps/api/src ./apps/api/src
RUN uv sync --locked --package scope-guard-api --no-dev --no-editable

FROM builder AS checks
RUN uv sync --locked --all-packages --all-groups --no-editable
# The frozen JOSE/bcrypt compatibility test executes the frontend's Node fixture.
COPY --from=node:22-bookworm-slim /usr/local/bin/node /usr/local/bin/node
ENV PATH="/app/.venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

FROM python:3.12-slim AS runtime
ARG SOURCE_REVISION=unknown
LABEL org.opencontainers.image.revision=$SOURCE_REVISION
WORKDIR /app/backend
ENV PATH="/app/.venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 SCOPE_GUARD_PRODUCTION=true
RUN useradd --system --uid 10001 --create-home scopeguard
COPY --from=builder --chown=scopeguard:scopeguard /app/.venv /app/.venv
COPY --chown=scopeguard:scopeguard backend/alembic.ini ./alembic.ini
COPY --chown=scopeguard:scopeguard backend/alembic ./alembic
COPY --chown=scopeguard:scopeguard apps/api/entrypoint.sh /app/entrypoint.sh
USER scopeguard

FROM runtime AS export-worker
COPY --chown=scopeguard:scopeguard apps/worker/main.py /app/export_worker.py
ENTRYPOINT ["python", "/app/export_worker.py"]

FROM runtime AS runner
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --start-period=24h --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=3)"
ENTRYPOINT ["/bin/sh", "/app/entrypoint.sh"]
CMD ["uvicorn", "scope_guard_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
