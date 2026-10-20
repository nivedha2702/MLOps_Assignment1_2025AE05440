from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_gke_cd_waits_for_successful_main_ci_and_uses_oidc():
    workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "cd-gke.yml").read_text())
    triggers = workflow.get("on", workflow.get(True))
    deploy = workflow["jobs"]["deploy"]
    steps = {step["name"]: step for step in deploy["steps"]}

    assert triggers["workflow_run"]["workflows"] == ["CI"]
    assert triggers["workflow_run"]["branches"] == ["main"]
    assert deploy["permissions"]["id-token"] == "write"
    assert "conclusion == 'success'" in deploy["if"]
    assert "event == 'push'" in deploy["if"]
    assert "GKE_DEPLOYMENT_ENABLED == 'true'" in deploy["if"]
    assert steps["Authenticate to Google Cloud with Workload Identity Federation"]["uses"].endswith(
        "/auth@v2"
    )
    assert "GCP_WORKLOAD_IDENTITY_PROVIDER" in str(
        steps["Authenticate to Google Cloud with Workload Identity Federation"]["with"]
    )
    assert "GCP_DEPLOY_SERVICE_ACCOUNT" in str(
        steps["Authenticate to Google Cloud with Workload Identity Federation"]["with"]
    )
    assert "docker push" in steps["Build and push the tested commit image"]["run"]
    assert "kubectl apply -f -" in steps["Deploy API to GKE"]["run"]
    assert "curl --fail" in steps["Verify public API and report its URL"]["run"]


def test_gke_overlay_serves_only_hardened_api_through_external_load_balancer():
    overlay = yaml.safe_load((ROOT / "k8s" / "gke" / "kustomization.yaml").read_text())
    resources = list(yaml.safe_load_all((ROOT / "k8s" / "gke" / "deployment.yaml").read_text()))
    deployment = next(resource for resource in resources if resource["kind"] == "Deployment")
    service = next(resource for resource in resources if resource["kind"] == "Service")
    container = deployment["spec"]["template"]["spec"]["containers"][0]

    assert overlay["namespace"] == "heart-disease-mlops"
    assert overlay["resources"] == ["deployment.yaml"]
    assert service["spec"]["type"] == "LoadBalancer"
    assert container["image"] == "heart-disease-api:local"
    assert container["readinessProbe"]["httpGet"]["path"] == "/health"
    assert container["securityContext"]["readOnlyRootFilesystem"] is True


def test_gke_deployer_role_is_namespace_scoped_to_api_resources():
    role, binding = yaml.safe_load_all((ROOT / "k8s" / "gke" / "deployer-rbac.yaml").read_text())

    assert role["kind"] == "Role"
    assert role["metadata"]["namespace"] == "heart-disease-mlops"
    assert binding["kind"] == "RoleBinding"
    assert binding["metadata"]["namespace"] == "heart-disease-mlops"
    assert binding["roleRef"]["name"] == role["metadata"]["name"]
    assert {rule["resources"][0] for rule in role["rules"]} == {"deployments", "services"}
