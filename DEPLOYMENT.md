# Local Kubernetes deployment

The assignment can be demonstrated on local Kubernetes using Docker Desktop Kubernetes or Minikube. This project does not configure or use GKE or any public cloud, and no public API URL is created.

Follow the [local Kubernetes deployment instructions](README.md#kubernetes-local-lab-deployment) to build/load the image, deploy the API and monitoring stack, port-forward the endpoints, and run the verification script.

GitHub Actions currently provides CI (lint, tests, training, and artifacts). Deployment to the local cluster is performed manually from your workstation; GitHub-hosted runners cannot directly access your local Docker Desktop or Minikube cluster. Capture your own run as evidence using [screenshots/README.md](screenshots/README.md).
