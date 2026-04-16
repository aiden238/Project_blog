FROM python:3.11-slim

WORKDIR /app

# uv 설치
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 의존성 먼저 (캐시 활용)
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev

# 소스 복사
COPY src/ ./src/
COPY sources/ ./sources/
COPY db/ ./db/

ENV PYTHONPATH=/app
