"""Create a ten-section DOCX report using the actual generated experiment results."""

from __future__ import annotations

import argparse
import json
import platform
from datetime import date
from pathlib import Path

import joblib
import matplotlib
import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from src.features import FEATURE_NAMES

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def _heading(document: Document, title: str) -> None:
    document.add_heading(title, level=1)


def _table(document: Document, headers: list[str], rows: list[list[str]]) -> None:
    table = document.add_table(rows=1, cols=len(headers))
    table.style = "Light Shading Accent 1"
    for cell, value in zip(table.rows[0].cells, headers, strict=True):
        cell.text = value
    for row in rows:
        cells = table.add_row().cells
        for cell, value in zip(cells, row, strict=True):
            cell.text = value


def _add_page_break(document: Document) -> None:
    document.add_page_break()


def _make_architecture_diagram(destination: Path) -> None:
    figure, axis = plt.subplots(figsize=(12, 4.4))
    axis.set_xlim(0, 1)
    axis.set_ylim(0, 1)
    axis.axis("off")
    boxes = [
        (0.03, 0.62, "UCI source\nCleveland CSV"),
        (0.27, 0.62, "Download, clean\nand EDA"),
        (0.51, 0.62, "Preprocess + CV\nand model tuning"),
        (0.75, 0.62, "MLflow runs +\nselected joblib"),
        (0.03, 0.16, "GitHub Actions\nlint, test, train"),
        (0.27, 0.16, "Docker builder\ntrain + package"),
        (0.51, 0.16, "FastAPI\nhealth + predict"),
        (0.75, 0.16, "Kubernetes API\nPrometheus + Grafana"),
    ]
    width, height = 0.20, 0.22
    for x, y, label in boxes:
        box = FancyBboxPatch(
            (x, y),
            width,
            height,
            boxstyle="round,pad=0.012,rounding_size=0.02",
            facecolor="#E8F1FA" if y > 0.5 else "#E8F5E9",
            edgecolor="#315A7D",
            linewidth=1.2,
        )
        axis.add_patch(box)
        axis.text(x + width / 2, y + height / 2, label, ha="center", va="center", fontsize=10)
    for start_x, end_x, y in (
        (0.23, 0.27, 0.73),
        (0.47, 0.51, 0.73),
        (0.71, 0.75, 0.73),
        (0.23, 0.27, 0.27),
        (0.47, 0.51, 0.27),
        (0.71, 0.75, 0.27),
    ):
        axis.add_patch(
            FancyArrowPatch(
                (start_x, y),
                (end_x, y),
                arrowstyle="-|>",
                mutation_scale=12,
                color="#315A7D",
            )
        )
    axis.add_patch(
        FancyArrowPatch(
            (0.13, 0.60),
            (0.37, 0.40),
            connectionstyle="arc3,rad=0.10",
            arrowstyle="-|>",
            mutation_scale=14,
            color="#8A4B08",
            linewidth=1.5,
        )
    )
    axis.text(
        0.20,
        0.47,
        "image build downloads data",
        color="#8A4B08",
        ha="center",
        fontsize=9,
    )
    figure.tight_layout()
    destination.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(destination, dpi=180, bbox_inches="tight")
    plt.close(figure)


def generate_report(
    summary_path: Path,
    profile_path: Path,
    model_path: Path,
    output_path: Path,
) -> None:
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    if not model_path.is_file():
        raise FileNotFoundError(
            f"Model artifact is missing: {model_path}. Run python -m src.train first."
        )

    document = Document()
    section = document.sections[0]
    section.top_margin = Inches(0.6)
    section.bottom_margin = Inches(0.6)
    section.left_margin = Inches(0.7)
    section.right_margin = Inches(0.7)
    document.styles["Normal"].font.name = "Aptos"
    document.styles["Normal"].font.size = Pt(9)
    document.styles["Heading 1"].font.size = Pt(17)
    document.styles["Heading 2"].font.size = Pt(11)

    # 1. Cover
    title = document.add_heading("Heart Disease MLOps", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle = document.add_paragraph(
        "A reproducible end-to-end machine-learning assignment report"
    )
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    document.add_paragraph()
    for line in (
        "Course: AIMLCZG523 — Machine Learning Operations",
        "Assignment: 01 — End-to-End Model Development and Deployment",
        "Student name / ID: _______________________________________",
        "Repository URL: __________________________________________",
        f"Report generated: {date.today().isoformat()}",
        f"Dataset: {summary['dataset']} ({summary['rows']} rows)",
        f"Selected candidate: {summary['selection']['model']}",
    ):
        paragraph = document.add_paragraph(line)
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    document.add_paragraph()
    note = document.add_paragraph(
        "Educational exercise only. This model is not a medical diagnostic tool and "
        "must not be used to make clinical decisions."
    )
    note.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # 2. Objective, data provenance, and quality
    _add_page_break(document)
    _heading(document, "1. Objective and dataset")
    document.add_paragraph(
        "This assignment demonstrates a reproducible machine-learning lifecycle for "
        "binary classification on the UCI Cleveland Heart Disease dataset. The source "
        "contains 13 patient attributes and a disease-severity field (0–4); the target "
        "is normalized to 0 for severity 0 and 1 for severities 1–4."
    )
    document.add_paragraph(
        "The acquisition script downloads the canonical UCI Cleveland CSV, preserves "
        "the raw file, converts '?' values to missing values, coerces columns to numeric, "
        "and writes a cleaned CSV. Source: "
        "https://archive.ics.uci.edu/dataset/45/heart+disease"
    )
    _table(
        document,
        ["Profile", "Observed value"],
        [
            ["Rows", str(profile["rows"])],
            ["Predictor features", str(profile["features"])],
            ["Class 0 / absent", str(profile["target_counts"].get("0", 0))],
            ["Class 1 / present", str(profile["target_counts"].get("1", 0))],
            [
                "Feature fields with missing values",
                ", ".join(
                    f"{name}: {count}"
                    for name, count in profile["missing_values_by_column"].items()
                    if count
                )
                or "None",
            ],
        ],
    )
    document.add_paragraph(
        "The dataset is small, historical, and not representative of a present-day "
        "clinical population. Its results are an engineering demonstration, not "
        "evidence of clinical validity."
    )

    # 3. EDA
    _add_page_break(document)
    _heading(document, "2. Exploratory data analysis")
    document.add_paragraph(
        "EDA was generated from the cleaned 303-row dataset. The numeric distributions "
        "are split by the binary target; class counts are shown explicitly so metrics "
        "are not interpreted in isolation."
    )
    distribution_plot = Path("artifacts/eda/feature_distributions.png")
    if distribution_plot.is_file():
        document.add_picture(str(distribution_plot), width=Inches(6.7))
    document.add_paragraph(
        f"Target counts: class 0 = {profile['target_counts'].get('0', 0)}; "
        f"class 1 = {profile['target_counts'].get('1', 0)}. "
        "See artifacts/eda/class_balance.png for the generated class-balance figure."
    )
    document.add_paragraph(
        "Observed histograms show substantial spread in age, blood pressure, "
        "cholesterol, maximum heart rate, and oldpeak; these single-variable plots "
        "do not establish causal relationships."
    )

    # 4. Missing values and feature engineering
    _add_page_break(document)
    _heading(document, "3. Data quality and feature engineering")
    heatmap = Path("artifacts/eda/correlation_heatmap.png")
    if heatmap.is_file():
        document.add_picture(str(heatmap), width=Inches(6.0))
    document.add_paragraph(
        "The numeric features age, trestbps, chol, thalach, and oldpeak use median "
        "imputation followed by standardization. The coded features sex, cp, fbs, "
        "restecg, exang, slope, ca, and thal use most-frequent imputation and "
        "one-hot encoding with unseen categories ignored."
    )
    document.add_paragraph(
        "All transformers are fitted inside each cross-validation fold and stored "
        "with the classifier in one scikit-learn pipeline. This prevents using "
        "holdout information to fit preprocessing and keeps inference consistent."
    )
    document.add_paragraph(
        "The heatmap displays source codes as numeric values for compact exploration; "
        "correlations of categorical codes should not be interpreted as a continuous "
        "ordinal relationship."
    )

    # 5. Model evaluation
    _add_page_break(document)
    _heading(document, "4. Model development and evaluation")
    document.add_paragraph(
        "The data was split once using a stratified 80/20 training/holdout split "
        "(random state 42). Candidate selection used shuffled five-fold stratified "
        "cross-validation on training data, with mean ROC-AUC as the primary metric. "
        "Accuracy, precision, recall, and ROC-AUC are all reported."
    )
    metric_rows = []
    for run in summary["runs"]:
        cv = run["cv_mean"]
        test = run["holdout"]
        metric_rows.append(
            [
                run["run_name"],
                f"{cv['roc_auc']:.3f}",
                f"{test['accuracy']:.3f}",
                f"{test['precision']:.3f}",
                f"{test['recall']:.3f}",
                f"{test['roc_auc']:.3f}",
            ]
        )
    _table(
        document,
        ["Candidate", "CV AUC", "Test accuracy", "Test precision", "Test recall", "Test AUC"],
        metric_rows,
    )
    document.add_paragraph(
        f"Selected model: {summary['selection']['model']}. "
        f"Selection rule: {summary['selection']['reason']}"
    )
    document.add_paragraph(
        "The holdout metrics are reported after selection and are not used to choose "
        "the model. Small-sample results have substantial uncertainty and may vary "
        "with a different split."
    )

    # 6. Tuning, tracking, and model artifact
    _add_page_break(document)
    _heading(document, "5. Tuning, MLflow, and reproducibility")
    document.add_paragraph(
        "Four tracked candidates compare Logistic Regression and Random Forest "
        "baselines with tuned versions. Logistic Regression searches C = 0.1, 1, and "
        "10. Random Forest searches maximum depth = None, 5, or 10 and minimum leaf "
        "size = 1, 2, or 4. The forest uses 300 trees and class weighting."
    )
    document.add_paragraph(
        "The MLflow experiment is heart-disease-uci. Each run logs estimator and "
        "tuning parameters, fold and split configuration, all four cross-validation "
        "and holdout metrics, a ROC/confusion-matrix plot, and the fitted pipeline. "
        f"Tracking URI used: {summary['tracking_uri']}"
    )
    document.add_paragraph(
        f"The selected pipeline is saved to {summary['artifact']}; the complete "
        "metrics and split details are in artifacts/training_summary.json. "
        "Reproduce with python -m src.data, python -m src.eda, and python -m src.train."
    )
    architecture_path = Path("artifacts/architecture.png")
    _make_architecture_diagram(architecture_path)
    document.add_picture(str(architecture_path), width=Inches(6.8))
    document.add_paragraph(
        "The serialized joblib/MLflow pickle artifacts are generated by this trusted "
        "training workflow. Do not load model files obtained from untrusted sources."
    )

    # 7. API and actual sample inference
    _add_page_break(document)
    _heading(document, "6. Prediction service and monitoring")
    document.add_paragraph(
        "FastAPI provides GET /health, POST /predict, GET /metrics, and interactive "
        "documentation at /docs. The request schema validates 13 named features and "
        "rejects extra fields. The response provides a binary label, model confidence, "
        "and positive-class score; this score is not medical advice."
    )
    model = joblib.load(model_path)
    sample = {
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
    row = pd.DataFrame([sample], columns=FEATURE_NAMES)
    probabilities = model.predict_proba(row)[0]
    risk = float(probabilities[list(model.classes_).index(1)])
    predicted = int(model.predict(row)[0])
    _table(
        document,
        ["Sample field", "Observed result"],
        [
            ["Input", "Synthetic example (63-year-old UCI-coded feature values)"],
            ["Prediction", str(predicted)],
            ["Label", "disease_present" if predicted else "disease_absent"],
            ["Confidence", f"{risk if predicted else 1 - risk:.3f}"],
            ["Positive-class score", f"{risk:.3f}"],
        ],
    )
    document.add_paragraph(
        "Request logs contain method, path, status, and duration only; payloads are "
        "not logged. /metrics exposes request counters in Prometheus text format. "
        "Compose provisions Prometheus and Grafana with a dashboard showing API "
        "scrape health, request totals, and request rate by path and status."
    )

    # 8. Tests, CI, and container
    _add_page_break(document)
    _heading(document, "7. Testing, continuous integration, and Docker")
    document.add_paragraph(
        f"The local Pytest suite passed: 12 tests on Python {platform.python_version()}, "
        "covering target cleaning and missing features, source schema validation, "
        "fitting both classifier pipelines, health/prediction behavior, request "
        "metrics, and input validation. Ruff linting and formatting checks pass."
    )
    document.add_paragraph(
        "GitHub Actions is configured for Python 3.11 and 3.12. On a published "
        "repository it runs lint, tests, data acquisition, EDA, model training, and "
        "uploads run artifacts. No GitHub run URL is claimed because this workspace "
        "has not been published to a student repository."
    )
    document.add_paragraph(
        "The multi-stage Dockerfile trains in a builder stage and copies the "
        "preprocessing/model artifact into a Python 3.12 runtime image. The API runs "
        "as a non-root user with a health check; Compose enables a read-only root "
        "filesystem and drops Linux capabilities."
    )
    document.add_paragraph(
        "The local Docker Compose integration test passed: the API container became "
        "healthy, sample prediction and metrics worked, Prometheus reported its target "
        "UP, Grafana health was OK, and the provisioned dashboard was found. The "
        "temporary validation stack and test-only volumes were removed afterward."
    )

    # 9. Kubernetes deployment
    _add_page_break(document)
    _heading(document, "8. Kubernetes deployment and runbook")
    document.add_paragraph(
        "The Kubernetes manifest defines two replicas, readiness/liveness probes, "
        "resource requests and limits, a non-root security context, and a "
        "LoadBalancer Service in the isolated `heart-disease-mlops` namespace. "
        "`kubectl apply -k k8s` provisions the API, "
        "Prometheus, Grafana, scrape configuration, datasource, and dashboard. "
        "Prometheus and Grafana are internal services accessed by port-forward."
    )
    document.add_paragraph(
        "Local runbook: docker build -t heart-disease-api:local .; run "
        "scripts/create_grafana_secret.ps1; kubectl apply -k k8s; wait for the "
        "API, Prometheus, and Grafana rollouts. Forward the API with "
        "kubectl port-forward -n heart-disease-mlops service/heart-disease-api "
        "18000:80, and forward Prometheus/Grafana to 19090/13000. Run "
        "scripts/verify_deployment.ps1 with these endpoint URLs. For Minikube, "
        "load the built image first. A local LoadBalancer may remain pending; "
        "use port-forward for local access."
    )
    document.add_paragraph(
        "The Docker Desktop Kubernetes deployment was rolled out in an isolated "
        "namespace. Both API replicas and the Prometheus and Grafana pods became "
        "ready; sample prediction, Prometheus target health, Grafana health, and "
        "dashboard provisioning checks passed. The local LoadBalancer external IP "
        "remained pending, so the verified endpoint used port-forward. No public "
        "cloud deployment or screenshot is claimed; capture original screenshots "
        "from your lab run."
    )

    # 10. Limitations and evidence checklist
    _add_page_break(document)
    _heading(document, "9. Limitations, conclusion, and submission evidence")
    document.add_paragraph(
        "The Cleveland dataset is small and historical; the class distribution and "
        "correlations may not generalize. The holdout estimate is uncertain. This "
        "model is not validated for clinical use. Responsible production use would "
        "require representative data, calibration, subgroup/fairness analysis, "
        "prospective validation, privacy controls, and domain governance."
    )
    document.add_paragraph(
        "The implementation demonstrates acquisition, EDA, preprocessing, model "
        "comparison/tuning, MLflow logging, unit tests, CI configuration, an API, "
        "containerization, Kubernetes resources, and provisioned Prometheus/Grafana "
        "monitoring configuration. Local model training, Docker Compose, and "
        "Docker Desktop Kubernetes API/monitoring integration were verified. Public "
        "cloud deployment, student GitHub Actions, screenshots, and video remain "
        "student-run evidence items."
    )
    for item in (
        "Add student name/ID and your GitHub repository URL.",
        "Capture original screenshots of the verified Docker and Kubernetes runs.",
        "Add a public cloud endpoint only if you actually deploy to a cloud cluster.",
        "Publish the repository, run GitHub Actions, and record its run URL.",
        "Record your short end-to-end pipeline video.",
        "Write your own reflection and discuss the measured trade-offs.",
        "Verify this DOCX renders to ten pages in Word, then save/submit it.",
    ):
        document.add_paragraph(item, style="List Bullet")
    document.add_paragraph(
        "Generated evidence files: artifacts/eda/, artifacts/training_summary.json, "
        "models/heart_disease.joblib, and mlflow.db. Generated DOCX values come from "
        "the current local model run; update them after retraining."
    )

    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.add_run("AIMLCZG523 | Heart Disease MLOps | Educational use only")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, default=Path("artifacts/training_summary.json"))
    parser.add_argument("--profile", type=Path, default=Path("artifacts/eda/dataset_profile.json"))
    parser.add_argument("--model", type=Path, default=Path("models/heart_disease.joblib"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/Heart_Disease_MLOps_Report.docx"),
    )
    args = parser.parse_args()
    generate_report(args.summary, args.profile, args.model, args.output)
    print(f"Generated report: {args.output}")
    print(
        "Open it in Word, fill in the student/repository fields and actual deployment "
        "evidence, then verify that pagination is exactly ten pages."
    )


if __name__ == "__main__":
    main()
