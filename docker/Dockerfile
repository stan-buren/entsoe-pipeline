FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock* /app/

RUN uv pip install --system -r pyproject.toml

COPY . /app

RUN uv pip install --system --no-deps -e .

ENV PYTHONPATH=/app/src
