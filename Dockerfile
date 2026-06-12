FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_SYSTEM_PYTHON=1

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

COPY . .

EXPOSE 8501

CMD ["uv", "run", "streamlit", "run", "src/app.py", "--server.address", "0.0.0.0", "--server.port", "8501"]
