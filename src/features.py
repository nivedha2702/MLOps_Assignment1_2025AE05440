"""Shared feature schema and serializable preprocessing/model pipelines."""

from __future__ import annotations

from typing import Literal

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

NUMERIC_FEATURES = ["age", "trestbps", "chol", "thalach", "oldpeak"]
CATEGORICAL_FEATURES = [
    "sex",
    "cp",
    "fbs",
    "restecg",
    "exang",
    "slope",
    "ca",
    "thal",
]
FEATURE_NAMES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
ModelName = Literal["logistic_regression", "random_forest"]


def build_preprocessor() -> ColumnTransformer:
    """Build imputers, numeric scaling, and one-hot categorical encoding."""
    numeric = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    return ColumnTransformer(
        [
            ("numeric", numeric, NUMERIC_FEATURES),
            ("categorical", categorical, CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )


def build_pipeline(
    model_name: ModelName,
    *,
    random_state: int = 42,
    model_params: dict[str, object] | None = None,
) -> Pipeline:
    """Return an end-to-end estimator so training and serving share preprocessing."""
    params = model_params or {}
    if model_name == "logistic_regression":
        estimator = LogisticRegression(max_iter=2000, random_state=random_state, **params)
    elif model_name == "random_forest":
        estimator = RandomForestClassifier(
            n_estimators=300,
            random_state=random_state,
            class_weight="balanced",
            n_jobs=1,
            **params,
        )
    else:
        raise ValueError(f"Unsupported model: {model_name}")
    return Pipeline(
        [
            ("preprocessor", build_preprocessor()),
            ("classifier", estimator),
        ]
    )
