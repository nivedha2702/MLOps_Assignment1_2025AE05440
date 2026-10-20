"""FastAPI prediction service with request logs and Prometheus-compatible metrics."""

from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path
from typing import Annotated

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field

from src.features import FEATURE_NAMES

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
LOGGER = logging.getLogger("heart_disease_api")
MODEL_PATH = Path(os.getenv("MODEL_PATH", "models/heart_disease.joblib"))
_model = None
_metrics_lock = threading.Lock()
_request_counts: dict[tuple[str, int], int] = {}

app = FastAPI(
    title="Heart Disease Risk API",
    description="Educational binary classifier using the UCI Cleveland Heart Disease dataset.",
    version="1.0.0",
)


class HeartDiseaseFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid")

    age: Annotated[float, Field(ge=1, le=120, description="Age in years")]
    sex: Annotated[int, Field(ge=0, le=1, description="UCI code: 1 = male, 0 = female")]
    cp: Annotated[int, Field(ge=1, le=4, description="UCI chest-pain type code")]
    trestbps: Annotated[float, Field(ge=50, le=300, description="Resting blood pressure (mm Hg)")]
    chol: Annotated[float, Field(ge=50, le=1000, description="Serum cholesterol (mg/dl)")]
    fbs: Annotated[int, Field(ge=0, le=1, description="Fasting blood sugar > 120 mg/dl")]
    restecg: Annotated[int, Field(ge=0, le=2, description="UCI resting ECG code")]
    thalach: Annotated[float, Field(ge=40, le=250, description="Maximum heart rate achieved")]
    exang: Annotated[int, Field(ge=0, le=1, description="Exercise-induced angina")]
    oldpeak: Annotated[float, Field(ge=0, le=10, description="ST depression induced by exercise")]
    slope: Annotated[int, Field(ge=1, le=3, description="UCI peak-exercise ST slope code")]
    ca: Annotated[float, Field(ge=0, le=4, description="Major vessels colored by fluoroscopy")]
    thal: Annotated[int, Field(ge=3, le=7, description="UCI thalassemia code")]


class PredictionResponse(BaseModel):
    prediction: int = Field(description="1 indicates disease present; 0 indicates absent")
    label: str
    confidence: float = Field(ge=0, le=1)
    risk_probability: float = Field(ge=0, le=1)


def _load_model():
    global _model
    if _model is None:
        if not MODEL_PATH.is_file():
            LOGGER.error("Packaged model is missing: %s", MODEL_PATH)
            raise HTTPException(
                status_code=503,
                detail="Model artifact is unavailable; train the model before serving.",
            )
        _model = joblib.load(MODEL_PATH)
    return _model


@app.middleware("http")
async def log_requests(request: Request, call_next):
    started = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        elapsed = time.perf_counter() - started
        path = request.url.path
        if path not in {"/health", "/predict", "/metrics", "/docs", "/openapi.json", "/redoc"}:
            path = "/other"
        with _metrics_lock:
            key = (path, status)
            _request_counts[key] = _request_counts.get(key, 0) + 1
        LOGGER.info(
            "request method=%s path=%s status=%d duration_seconds=%.6f",
            request.method,
            path,
            status,
            elapsed,
        )


@app.get("/health")
def health() -> dict[str, str]:
    _load_model()
    return {"status": "ok"}


@app.get("/metrics", response_class=PlainTextResponse)
def metrics() -> str:
    with _metrics_lock:
        counters = sorted(_request_counts.items())
    lines = [
        "# HELP heart_api_requests_total Total HTTP requests by path and status.",
        "# TYPE heart_api_requests_total counter",
    ]
    for (path, status), count in counters:
        escaped_path = path.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'heart_api_requests_total{{path="{escaped_path}",status="{status}"}} {count}')
    return PlainTextResponse(
        "\n".join(lines) + "\n",
        media_type="text/plain; version=0.0.4",
    )


@app.post("/predict", response_model=PredictionResponse)
def predict(payload: HeartDiseaseFeatures) -> PredictionResponse:
    model = _load_model()
    row = pd.DataFrame([payload.model_dump()], columns=FEATURE_NAMES)
    probabilities = model.predict_proba(row)[0]
    positive_index = list(model.classes_).index(1)
    risk = float(probabilities[positive_index])
    prediction = int(model.predict(row)[0])
    confidence = risk if prediction == 1 else 1 - risk
    return PredictionResponse(
        prediction=prediction,
        label="disease_present" if prediction == 1 else "disease_absent",
        confidence=confidence,
        risk_probability=risk,
    )
