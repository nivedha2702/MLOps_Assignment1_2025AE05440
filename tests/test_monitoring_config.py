import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_prometheus_targets_match_docker_and_kubernetes_services():
    docker_config = yaml.safe_load(
        (ROOT / "monitoring" / "prometheus-docker.yml").read_text(encoding="utf-8")
    )
    kubernetes_config = yaml.safe_load(
        (ROOT / "k8s" / "monitoring" / "prometheus.yml").read_text(encoding="utf-8")
    )

    assert docker_config["scrape_configs"][0]["static_configs"][0]["targets"] == ["heart-api:8000"]
    assert kubernetes_config["scrape_configs"][0]["static_configs"][0]["targets"] == [
        "heart-disease-api:80"
    ]


def test_grafana_dashboard_contains_live_api_metrics():
    dashboard = json.loads(
        (ROOT / "k8s" / "monitoring" / "heart-disease-api.json").read_text(encoding="utf-8")
    )
    expressions = [target["expr"] for panel in dashboard["panels"] for target in panel["targets"]]

    assert dashboard["uid"] == "heart-disease-api"
    assert 'up{job="heart-disease-api"}' in expressions
    assert any("heart_api_requests_total" in expression for expression in expressions)


def test_kustomize_generators_match_monitoring_configmap_references():
    kustomization = yaml.safe_load(
        (ROOT / "k8s" / "kustomization.yaml").read_text(encoding="utf-8")
    )
    assert kustomization["namespace"] == "heart-disease-mlops"
    assert "namespace.yaml" in kustomization["resources"]
    configmaps = {
        item["name"]: {Path(file).name for file in item["files"]}
        for item in kustomization["configMapGenerator"]
    }
    assert configmaps["heart-prometheus-config"] == {"prometheus.yml"}
    assert configmaps["grafana-datasource"] == {"grafana-datasource.yml"}
    assert configmaps["grafana-dashboard-provider"] == {"grafana-dashboards.yml"}
    assert configmaps["heart-grafana-dashboard"] == {"heart-disease-api.json"}


def test_kubernetes_stack_has_private_monitoring_services_and_password_secret():
    resources = list(
        yaml.safe_load_all((ROOT / "k8s" / "monitoring-stack.yaml").read_text(encoding="utf-8"))
    )
    services = {
        resource["metadata"]["name"]: resource
        for resource in resources
        if resource["kind"] == "Service"
    }
    deployments = {
        resource["metadata"]["name"]: resource
        for resource in resources
        if resource["kind"] == "Deployment"
    }
    grafana_container = deployments["grafana"]["spec"]["template"]["spec"]["containers"][0]
    password_env = next(
        item for item in grafana_container["env"] if item["name"] == "GF_SECURITY_ADMIN_PASSWORD"
    )

    assert services["prometheus"]["spec"]["type"] == "ClusterIP"
    assert services["grafana"]["spec"]["type"] == "ClusterIP"
    assert password_env["valueFrom"]["secretKeyRef"] == {
        "name": "grafana-admin",
        "key": "admin-password",
    }
