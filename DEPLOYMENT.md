# Cloud Run deployment guide

This repository now includes a GitHub Actions workflow to build the Dockerized API and deploy it to Google Cloud Run.

## Required GitHub secrets

Add the following repository secrets in GitHub:

- `GCP_PROJECT_ID`: your Google Cloud project ID
- `GCP_REGION`: e.g. `us-central1`
- `GCP_SERVICE_NAME`: the Cloud Run service name, e.g. `heart-disease-api`
- `GCP_SA_KEY`: the JSON contents of a Google Cloud service account key with the following roles:
  - Cloud Run Admin
  - Service Account User
  - Viewer
  - Storage Admin (if using GCR image registry)

## Triggering deployment

The workflow runs automatically on pushes to `main` when the app source changes, or can be started manually from the GitHub Actions tab using `workflow_dispatch`.

## Output

After a successful deployment, the workflow prints the public URL in the logs:

- `https://<service-name>-<hash>.run.app`

This URL is not committed to source control: it is generated at deployment time.

## Example

```bash
gcloud run deploy heart-disease-api \
  --image gcr.io/<project-id>/heart-disease-api:<sha> \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated
```

## Health-check example

```bash
curl https://<service-name>-<hash>.run.app/health
curl -X POST https://<service-name>-<hash>.run.app/predict \
  -H "Content-Type: application/json" \
  -d '{
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
    "thal": 6
  }'
```
