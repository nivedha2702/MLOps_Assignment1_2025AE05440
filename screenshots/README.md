# Assignment evidence

Save your own screenshots here after running the project in your lab environment:

1. `01-eda.png` — generated EDA plots and dataset profile.
2. `02-mlflow.png` — MLflow experiment comparing the four tracked model runs.
3. `03-tests-ci.png` — passing local tests and GitHub Actions workflow.
4. `04-docker-api.png` — healthy Docker container and a successful `/predict` response.
5. `05-kubernetes.png` — `kubectl get pods,services,endpoints` showing ready API pods, a `LoadBalancer` Service and its endpoints, plus a successful `/health` or `/predict` request through the local port-forward. Docker Desktop's LoadBalancer IP may be cluster-internal and unreachable from Windows; do not label it a public URL.
6. `06-monitoring.png` — Grafana's **Heart Disease API Monitoring** dashboard with target health and request metrics. Optionally include Prometheus `/targets` showing the API is **UP**.
Do not add fabricated deployment screenshots or credentials. For a local-only lab deployment, include terminal screenshots showing the equivalent checks. A local LoadBalancer Service is evidence of Kubernetes Service exposure, not a public-cloud deployment.
