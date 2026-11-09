# Build from the repository root:
#   docker build -f backend/Dockerfile -t nba-analytics-api .
#   docker run -p 8000:8000 nba-analytics-api

# --- Stage 1: build the serving database from the committed datasets and models ---------------------
FROM python:3.11-slim AS data

WORKDIR /repo
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY config ./config
COPY src ./src
COPY data ./data
COPY saved_models ./saved_models
RUN python -m src.export_db


# --- Stage 2: the API, with only FastAPI, Pydantic and Uvicorn installed -----------------------------
FROM python:3.11-slim

WORKDIR /srv
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 PORT=8000

COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/app ./app
COPY --from=data /repo/backend/data ./data

RUN useradd --system --no-create-home api
USER api

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/api/v1/health')"

# Many hosts set $PORT, so read it at runtime.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers"]
