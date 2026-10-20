# Assignment evidence

Save your own screenshots here after running the project in your lab environment:

1. `01-eda.png` — generated EDA plots and dataset profile.
![class-balance](../artifacts/eda/class_balance.png)
![correlation-heatmap](../artifacts/eda/correlation_heatmap.png)
![feature-distributions](../artifacts/eda/feature_distributions.png)
dataset profile :
{
  "rows": 303,
  "features": 13,
  "missing_values_by_column": {
    "age": 0,
    "trestbps": 0,
    "chol": 0,
    "thalach": 0,
    "oldpeak": 0,
    "sex": 0,
    "cp": 0,
    "fbs": 0,
    "restecg": 0,
    "exang": 0,
    "slope": 0,
    "ca": 4,
    "thal": 2
  },
  "target_counts": {
    "0": 164,
    "1": 139
  },
  "plots": [
    "feature_distributions.png",
    "class_balance.png",
    "correlation_heatmap.png"
  ]
}

2. `02-mlflow.png` — MLflow experiment comparing the four tracked model runs.
![Experiment tracking](image.png)
![Training summary](image-1.png)
![Random Forest Baseline Overview](image-2.png)
![Random Forest Baseline Artifacts](image-3.png)
![Logistic Regression Baseline Overview](image-4.png)
![Logistic Regression Baseline Artifacts](image-5.png)
![Random Forest Tuned Overview](image-6.png)
![Random Forest Tuned Artifacts](image-7.png)
![Logistic Regression Tuned Overview](image-8.png)
![Logistic Regression Tuned Artifacts](image-9.png)

3. `03-tests-ci.png` — passing local tests and GitHub Actions workflow.
![Every push triggers the pipeline](image-10.png)
![Two jobs run for python 3.11 and 3.12](image-11.png)
![CI workflow logs](image-12.png)

4. `04-docker-api.png` — healthy Docker container and a successful `/predict` response.
![Docker Containers](image-13.png)
![Docker images](image-14.png)
![Successful Prediction via /predict API](image-15.png)
5. `05-kubernetes.png` — `kubectl get pods,services,endpoints` showing ready API pods, a `LoadBalancer` Service and its endpoints, plus a successful `/health` or `/predict` request through the local port-forward. Docker Desktop's LoadBalancer IP may be cluster-internal and unreachable from Windows; do not label it a public URL.
![Kubernetes Cluster](image-16.png)
![Kubernetes](image-17.png)
![Deployment verification script response](image-18.png)

6. `06-monitoring.png` — Grafana's **Heart Disease API Monitoring** dashboard with target health and request metrics. Optionally include Prometheus `/targets` showing the API is **UP**.
![Grafana Dashboard](image-19.png)
![Prometheus](image-20.png)
