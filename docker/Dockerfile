FROM python:3.14-slim

# Install uv from its official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency manifests first — layer is cached until they change
COPY pyproject.toml uv.lock README.md LICENSE ./

# Install only third-party dependencies (not the project itself).
# BuildKit cache mount persists uv's package cache across builds.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Copy application code (cheap — only ~2 MB)
COPY src/ /app/src/
COPY jobs/ /app/jobs/
COPY config/ /app/config/

# Install the project itself (instantly — deps already cached)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

ENV PYTHONPATH=/app/src
ENV PATH=/app/.venv/bin:$PATH
