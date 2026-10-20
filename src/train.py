"""Compare, tune, track, and package reproducible Heart Disease classifiers."""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
from typing import Any

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import (
    GridSearchCV,
    StratifiedKFold,
    cross_validate,
    train_test_split,
)
from sklearn.pipeline import Pipeline

from src.data import load_dataset
from src.features import FEATURE_NAMES, build_pipeline

LOGGER = logging.getLogger(__name__)
RANDOM_STATE = 42
TEST_SIZE = 0.2
N_SPLITS = 5
SCORING = "roc_auc"


def _metric_values(y_true: pd.Series, predictions: np.ndarray, probabilities: np.ndarray) -> dict:
    return {
        "accuracy": float(accuracy_score(y_true, predictions)),
        "precision": float(precision_score(y_true, predictions, zero_division=0)),
        "recall": float(recall_score(y_true, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, probabilities)),
    }


def _evaluation_plot(y_true: pd.Series, probabilities: np.ndarray, path: Path) -> None:
    fpr, tpr, _ = roc_curve(y_true, probabilities)
    matrix = confusion_matrix(y_true, probabilities >= 0.5)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].plot(fpr, tpr, label=f"AUC = {roc_auc_score(y_true, probabilities):.3f}")
    axes[0].plot([0, 1], [0, 1], linestyle="--", color="gray")
    axes[0].set(xlabel="False positive rate", ylabel="True positive rate", title="ROC curve")
    axes[0].legend(loc="lower right")
    image = axes[1].imshow(matrix, cmap="Blues")
    axes[1].set(
        xlabel="Predicted label",
        ylabel="True label",
        title="Holdout confusion matrix",
        xticks=[0, 1],
        yticks=[0, 1],
    )
    for row in range(2):
        for column in range(2):
            axes[1].text(column, row, str(matrix[row, column]), ha="center", va="center")
    fig.colorbar(image, ax=axes[1], fraction=0.046)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _tune(
    name: str,
    x_train: pd.DataFrame,
    y_train: pd.Series,
    cv: StratifiedKFold,
) -> tuple[Pipeline, dict[str, Any], dict[str, float]]:
    if name == "logistic_regression":
        param_grid = {"classifier__C": [0.1, 1.0, 10.0]}
    else:
        param_grid = {
            "classifier__max_depth": [None, 5, 10],
            "classifier__min_samples_leaf": [1, 2, 4],
        }
    search = GridSearchCV(
        build_pipeline(name),
        param_grid=param_grid,
        scoring={
            "accuracy": "accuracy",
            "precision": "precision",
            "recall": "recall",
            "roc_auc": SCORING,
        },
        refit=SCORING,
        cv=cv,
        n_jobs=1,
        return_train_score=False,
    )
    search.fit(x_train, y_train)
    best_index = int(search.best_index_)
    cv_metrics = {
        metric: float(search.cv_results_[f"mean_test_{metric}"][best_index])
        for metric in ("accuracy", "precision", "recall", "roc_auc")
    }
    return (
        search.best_estimator_,
        {
            "best_params": search.best_params_,
        },
        cv_metrics,
    )


def train(
    data: pd.DataFrame,
    *,
    output_model: str | Path = "models/heart_disease.joblib",
    output_dir: str | Path = "artifacts",
    tracking: bool = True,
) -> dict:
    if "target" not in data.columns or set(data["target"].dropna().unique()) != {0, 1}:
        raise ValueError("Training data must include a binary target column containing 0 and 1.")
    missing = sorted(set(FEATURE_NAMES) - set(data.columns))
    if missing:
        raise ValueError(f"Training data is missing required features: {missing}")
    x = data[FEATURE_NAMES]
    y = data["target"].astype("int64")
    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y,
    )
    cv = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    model_path = Path(output_model)
    model_path.parent.mkdir(parents=True, exist_ok=True)

    if tracking:
        import mlflow
        import mlflow.sklearn

        tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
        mlflow.set_tracking_uri(
            tracking_uri if tracking_uri else f"sqlite:///{Path('mlflow.db').resolve().as_posix()}"
        )
        mlflow.set_experiment("heart-disease-uci")

    candidates: list[tuple[str, Pipeline, dict[str, Any], dict[str, float]]] = []
    for name in ("logistic_regression", "random_forest"):
        baseline = build_pipeline(name)
        baseline.fit(x_train, y_train)
        cv_result = cross_validate(
            baseline,
            x_train,
            y_train,
            cv=cv,
            scoring={
                "accuracy": "accuracy",
                "precision": "precision",
                "recall": "recall",
                "roc_auc": SCORING,
            },
            n_jobs=1,
        )
        scores = {
            metric: float(np.mean(cv_result[f"test_{metric}"]))
            for metric in ("accuracy", "precision", "recall", "roc_auc")
        }
        candidates.append((f"{name}_baseline", baseline, {"tuned": False}, scores))
        tuned, tuning, tuned_scores = _tune(name, x_train, y_train, cv)
        candidates.append((f"{name}_tuned", tuned, tuning, tuned_scores))

    candidates.sort(key=lambda candidate: candidate[3]["roc_auc"], reverse=True)
    summaries: list[dict] = []
    best_model: Pipeline | None = None
    best_holdout_score = -1.0
    for run_name, pipeline, tuning, cv_metrics in candidates:
        pipeline.fit(x_train, y_train)
        probabilities = pipeline.predict_proba(x_test)[:, 1]
        holdout = _metric_values(y_test, pipeline.predict(x_test), probabilities)
        figure_path = output / f"{run_name}_evaluation.png"
        _evaluation_plot(y_test, probabilities, figure_path)
        result = {
            "run_name": run_name,
            "cv_mean": cv_metrics,
            "holdout": holdout,
            "tuning": tuning,
        }
        summaries.append(result)
        if tracking:
            with mlflow.start_run(run_name=run_name):
                mlflow.log_param("random_state", RANDOM_STATE)
                mlflow.log_param("test_size", TEST_SIZE)
                mlflow.log_param("cv_splits", N_SPLITS)
                mlflow.log_param("selection_metric", SCORING)
                mlflow.log_params(
                    {
                        key: str(value)
                        for key, value in pipeline.named_steps["classifier"].get_params().items()
                    }
                )
                mlflow.log_params({f"tuning_{key}": str(value) for key, value in tuning.items()})
                mlflow.log_metrics({f"cv_{key}": value for key, value in cv_metrics.items()})
                mlflow.log_metrics({f"holdout_{key}": value for key, value in holdout.items()})
                mlflow.log_artifact(str(figure_path), artifact_path="evaluation")
                mlflow.sklearn.log_model(
                    pipeline,
                    artifact_path="model",
                    serialization_format="pickle",
                )
        if cv_metrics["roc_auc"] > best_holdout_score:
            best_model = pipeline
            best_holdout_score = cv_metrics["roc_auc"]

    assert best_model is not None
    joblib.dump(best_model, model_path)
    final_results = {
        "dataset": "UCI Heart Disease (Cleveland; target: 0 vs 1-4)",
        "rows": int(len(data)),
        "features": FEATURE_NAMES,
        "split": {"test_size": TEST_SIZE, "random_state": RANDOM_STATE, "stratified": True},
        "cross_validation": {"folds": N_SPLITS, "selection_metric": SCORING},
        "selection": {
            "model": candidates[0][0],
            "reason": "Highest mean stratified cross-validation ROC-AUC on training data.",
        },
        "runs": summaries,
        "artifact": str(model_path),
        "tracking_uri": mlflow.get_tracking_uri() if tracking else None,
    }
    summary_path = output / "training_summary.json"
    summary_path.write_text(json.dumps(final_results, indent=2), encoding="utf-8")
    if tracking:
        with mlflow.start_run(run_name="training-summary"):
            mlflow.log_artifact(str(summary_path))
    LOGGER.info("Selected %s; saved model to %s", candidates[0][0], model_path)
    LOGGER.info("Training summary written to %s", summary_path)
    return final_results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=None)
    parser.add_argument("--output-model", type=Path, default=Path("models/heart_disease.joblib"))
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts"))
    parser.add_argument(
        "--no-mlflow",
        action="store_true",
        help="Train without starting MLflow runs.",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    train(
        load_dataset(args.data),
        output_model=args.output_model,
        output_dir=args.output_dir,
        tracking=not args.no_mlflow,
    )


if __name__ == "__main__":
    main()
