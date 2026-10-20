FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /build
COPY requirements-api.txt requirements-api.txt
COPY requirements-build.txt requirements-build.txt
RUN python -m pip install --upgrade pip && python -m pip install -r requirements-build.txt
COPY src src
RUN python -m src.data --raw-path /tmp/processed.cleveland.data --output /tmp/heart_disease.csv \
    && python -m src.train --data /tmp/heart_disease.csv --output-model /build/models/heart_disease.joblib \
       --output-dir /build/artifacts --no-mlflow

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MODEL_PATH=/app/models/heart_disease.joblib
WORKDIR /app
COPY requirements-api.txt requirements-api.txt
RUN python -m pip install --upgrade pip && python -m pip install -r requirements-api.txt \
    && useradd --create-home --uid 10001 appuser
COPY --from=builder /build/src /app/src
COPY --from=builder /build/models/heart_disease.joblib /app/models/heart_disease.joblib
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/health', timeout=3)"
CMD ["uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "8000"]
