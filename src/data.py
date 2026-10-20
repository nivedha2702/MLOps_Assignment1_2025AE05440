"""Download and clean the Cleveland Heart Disease data from the UCI repository."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from urllib.request import urlopen

import pandas as pd

LOGGER = logging.getLogger(__name__)
DATA_URL = (
    "https://archive.ics.uci.edu/ml/machine-learning-databases/heart-disease/"
    "processed.cleveland.data"
)
RAW_COLUMNS = [
    "age",
    "sex",
    "cp",
    "trestbps",
    "chol",
    "fbs",
    "restecg",
    "thalach",
    "exang",
    "oldpeak",
    "slope",
    "ca",
    "thal",
    "target",
]
RAW_DIR = Path("data/raw")
PROCESSED_PATH = Path("data/processed/heart_disease.csv")


def clean_dataset(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize the UCI columns, preserve missing features for pipeline imputation,
    and map the original 0-4 disease severity to a binary target.
    """
    if frame.shape[1] != len(RAW_COLUMNS):
        raise ValueError(f"Expected {len(RAW_COLUMNS)} UCI columns, received {frame.shape[1]}.")
    cleaned = frame.copy()
    cleaned.columns = RAW_COLUMNS
    cleaned = cleaned.replace("?", pd.NA)
    for column in RAW_COLUMNS:
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")
    cleaned = cleaned.dropna(subset=["target"])
    cleaned["target"] = (cleaned["target"] > 0).astype("int64")
    if cleaned.empty:
        raise ValueError("The source data has no rows with a valid target.")
    if not set(cleaned["target"].unique()).issubset({0, 1}):
        raise ValueError("Target normalization failed; expected binary labels 0 and 1.")
    return cleaned.reset_index(drop=True)


def download_dataset(
    raw_path: str | Path = RAW_DIR / "processed.cleveland.data",
    processed_path: str | Path = PROCESSED_PATH,
) -> Path:
    """Fetch the canonical Cleveland file and persist its cleaned CSV."""
    raw_file = Path(raw_path)
    clean_file = Path(processed_path)
    raw_file.parent.mkdir(parents=True, exist_ok=True)
    clean_file.parent.mkdir(parents=True, exist_ok=True)
    LOGGER.info("Downloading the UCI Cleveland dataset from %s", DATA_URL)
    try:
        with urlopen(DATA_URL, timeout=30) as response:
            if response.status != 200:
                raise RuntimeError(f"UCI download returned HTTP {response.status}.")
            content = response.read()
    except (OSError, TimeoutError) as exc:
        raise RuntimeError(f"Could not download the UCI dataset from {DATA_URL}: {exc}") from exc
    if not content:
        raise RuntimeError(f"The UCI dataset download from {DATA_URL} was empty.")
    raw_file.write_bytes(content)
    raw = pd.read_csv(raw_file, header=None, names=RAW_COLUMNS, na_values="?")
    cleaned = clean_dataset(raw)
    cleaned.to_csv(clean_file, index=False)
    LOGGER.info(
        "Saved %s cleaned patient rows to %s (raw source: %s)",
        len(cleaned),
        clean_file,
        raw_file,
    )
    return clean_file


def load_dataset(path: str | Path | None = None) -> pd.DataFrame:
    """Load a cleaned CSV, downloading the source when the default is absent."""
    selected = Path(path) if path is not None else PROCESSED_PATH
    if path is None and not selected.exists():
        download_dataset()
    if not selected.is_file():
        raise FileNotFoundError(f"Dataset not found: {selected}")
    return clean_dataset(pd.read_csv(selected))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-path", type=Path, default=RAW_DIR / "processed.cleveland.data")
    parser.add_argument("--output", type=Path, default=PROCESSED_PATH)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    download_dataset(args.raw_path, args.output)


if __name__ == "__main__":
    main()
