# syntax=docker/dockerfile:1

FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_SYSTEM_PYTHON=1

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

COPY . .
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

EXPOSE 4573

CMD ["uv", "run", "uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "4573"]
