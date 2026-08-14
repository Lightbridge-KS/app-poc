# syntax=docker/dockerfile:1

# ── builder ───────────────────────────────────────────────────────────────────
# Same base as the runtime stage on purpose: the venv records an absolute
# interpreter path, so a builder with a different Python would produce a venv
# that cannot start in the runtime stage.
FROM python:3.12-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependency layer, cached independently of application code.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# ── runtime ───────────────────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

RUN useradd --create-home --uid 10001 appuser

WORKDIR /app
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --chown=appuser:appuser app ./app

USER appuser
EXPOSE 8050

# Hits /_dash-layout rather than /: `/` is served by Flask and would return 200
# even if Dash itself failed to initialize. `python -c` instead of curl keeps the
# slim image free of an extra apt layer.
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8050/_dash-layout').read()"]

# gunicorn, not `app.run` — Dash's own docs call app.run dev-only. Two
# containerization-critical bits:
#   --bind 0.0.0.0  Dash/Flask default to 127.0.0.1, which inside a container is
#                   the container's own loopback and unreachable from the host.
#   --chdir         app/ has no __init__.py, so `app.app:server` is ambiguous;
#                   chdir into it and import the module plainly as `app:server`.
# 4 workers is safe here only because Dash callbacks are stateless HTTP.
CMD ["gunicorn", "--chdir", "/app/app", "--bind", "0.0.0.0:8050", "--workers", "4", "app:server"]
