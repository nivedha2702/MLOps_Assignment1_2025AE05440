# Google Kubernetes Engine deployment

This repository's automated cloud deployment target is **Google Kubernetes Engine (GKE)**, not Cloud Run. The `CD - GKE` workflow waits for a successful push-triggered CI run on `main`, builds and pushes the tested commit to Artifact Registry, deploys the API, waits for rollout, and checks the public `/health` endpoint.

Complete the GCP project, GKE cluster, Artifact Registry, Workload Identity Federation, namespace-scoped Kubernetes permissions, and GitHub environment setup in the [GKE continuous deployment section of the README](README.md#gke-continuous-deployment-optional-requires-google-cloud-setup). The workflow uses short-lived OIDC credentials; do not create a service-account JSON key.

**No public API URL exists until you configure those cloud resources and GitHub environment values and the CD run succeeds.** When deployed, the Actions log prints the assigned public API URL, health endpoint, and API documentation URL. The URL can change if the cluster or LoadBalancer Service is recreated.

The public API is an educational demonstration, served over HTTP, and must not receive real patient information.
