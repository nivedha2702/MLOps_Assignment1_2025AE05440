from fastapi.testclient import TestClient

import src.api as api

client = TestClient(api.app)
SAMPLE = {
    "age": 63,
    "sex": 1,
    "cp": 1,
    "trestbps": 145,
    "chol": 233,
    "fbs": 1,
    "restecg": 2,
    "thalach": 150,
    "exang": 0,
    "oldpeak": 2.3,
    "slope": 3,
    "ca": 0,
    "thal": 6,
}


def test_health_endpoint(monkeypatch):
    monkeypatch.setattr(api, "_model", object())
    assert client.get("/health").json() == {"status": "ok"}


def test_predict_returns_binary_label_and_confidence(monkeypatch):
    class FakeModel:
        classes_ = [0, 1]

        def predict_proba(self, frame):
            assert frame.shape == (1, 13)
            return [[0.2, 0.8]]

        def predict(self, frame):
            return [1]

    monkeypatch.setattr(api, "_model", FakeModel())
    response = client.post("/predict", json=SAMPLE)
    assert response.status_code == 200
    assert response.json() == {
        "prediction": 1,
        "label": "disease_present",
        "confidence": 0.8,
        "risk_probability": 0.8,
    }


def test_predict_rejects_out_of_range_input():
    invalid = {**SAMPLE, "age": 200}
    assert client.post("/predict", json=invalid).status_code == 422


def test_metrics_exposes_observed_requests():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain; version=0.0.4" in response.headers["content-type"]
    assert "heart_api_requests_total" in response.text


def test_metrics_groups_unmatched_paths():
    assert client.get("/not-a-route/123").status_code == 404
    assert 'path="/other"' in client.get("/metrics").text
