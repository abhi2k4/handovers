# Backend image. Build context is the repository root (the app needs graph/: queries, schema, seed).
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    GRAPH_DIR=/app/graph

WORKDIR /app

# Dependencies first (cached layer), then the application code and graph definitions.
COPY app/backend/pyproject.toml app/backend/uv.lock ./
RUN uv sync --frozen --no-dev

COPY app/backend/ ./
COPY graph/ /app/graph/

EXPOSE 8000
CMD ["uv", "run", "--no-sync", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
