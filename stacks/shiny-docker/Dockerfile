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
    PATH="/app/.venv/bin:$PATH" \
    # No display in a container, so pin the headless backend rather than let
    # matplotlib guess. MPLCONFIGDIR must be writable by uid 10001 or every
    # single render logs a "matplotlib created a temporary cache" warning.
    MPLBACKEND=Agg \
    MPLCONFIGDIR=/home/appuser/.cache/matplotlib

RUN useradd --create-home --uid 10001 appuser

WORKDIR /app
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --chown=appuser:appuser app ./app

USER appuser

# Build the font cache now, at image-build time. Skip this and the very first
# plot a user requests pays a multi-second stall while matplotlib scans fonts.
RUN python -c "import matplotlib.pyplot"

EXPOSE 8000

# `python -c` instead of curl: keeps the slim image free of an extra apt layer.
# start-period is 30s, not 10s: importing polars + plotnine + matplotlib +
# statsmodels takes far longer than importing bare shiny did.
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/').read()"]

# --host 0.0.0.0 is the containerization-critical bit: Shiny's default bind is
# 127.0.0.1, which is unreachable from outside the container's netns.
CMD ["shiny", "run", "--host", "0.0.0.0", "--port", "8000", "app/app.py"]
