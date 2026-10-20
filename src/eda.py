"""Generate assignment-ready EDA plots and a compact dataset profile."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from src.data import load_dataset
from src.features import FEATURE_NAMES

LOGGER = logging.getLogger(__name__)


def create_eda(data: pd.DataFrame, output_dir: str | Path = "artifacts/eda") -> dict:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid", palette="colorblind")

    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    for axis, column in zip(
        axes.flat, ["age", "trestbps", "chol", "thalach", "oldpeak"], strict=False
    ):
        sns.histplot(data=data, x=column, hue="target", kde=True, element="step", ax=axis)
        axis.set_title(f"{column}: distribution by outcome")
    axes.flat[-1].axis("off")
    fig.tight_layout()
    fig.savefig(output / "feature_distributions.png", dpi=160)
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(7, 5))
    balance = data["target"].value_counts().sort_index()
    sns.barplot(x=balance.index.astype(str), y=balance.values, ax=axis)
    axis.set(
        title="Heart disease class balance",
        xlabel="Target (0 = absent, 1 = present)",
        ylabel="Patients",
    )
    for container in axis.containers:
        axis.bar_label(container)
    fig.tight_layout()
    fig.savefig(output / "class_balance.png", dpi=160)
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(12, 9))
    sns.heatmap(
        data[FEATURE_NAMES + ["target"]].corr(numeric_only=True),
        cmap="vlag",
        center=0,
        ax=axis,
    )
    axis.set_title("Feature correlation heatmap (categorical codes shown as UCI values)")
    fig.tight_layout()
    fig.savefig(output / "correlation_heatmap.png", dpi=160)
    plt.close(fig)

    profile = {
        "rows": int(len(data)),
        "features": int(len(FEATURE_NAMES)),
        "missing_values_by_column": {
            key: int(value) for key, value in data[FEATURE_NAMES].isna().sum().items()
        },
        "target_counts": {
            str(key): int(value)
            for key, value in data["target"].value_counts().sort_index().items()
        },
        "plots": [
            "feature_distributions.png",
            "class_balance.png",
            "correlation_heatmap.png",
        ],
    }
    (output / "dataset_profile.json").write_text(json.dumps(profile, indent=2), encoding="utf-8")
    LOGGER.info("Wrote EDA figures and profile to %s", output)
    return profile


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/eda"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    create_eda(load_dataset(args.data), args.output_dir)


if __name__ == "__main__":
    main()
