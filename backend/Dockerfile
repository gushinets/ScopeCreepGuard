FROM python:3.12-slim AS builder
WORKDIR /app
ENV UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
RUN pip install --no-cache-dir uv==0.11.19
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY src ./src
RUN uv sync --locked --no-dev --no-editable

FROM python:3.12-slim AS runner
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN useradd --system --uid 10001 --create-home scopeguard
COPY --from=builder --chown=scopeguard:scopeguard /app/.venv ./.venv
COPY --chown=scopeguard:scopeguard alembic.ini ./alembic.ini
COPY --chown=scopeguard:scopeguard alembic ./alembic
USER scopeguard
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=3)"
CMD ["uvicorn", "scope_guard.main:app", "--host", "0.0.0.0", "--port", "8000"]
