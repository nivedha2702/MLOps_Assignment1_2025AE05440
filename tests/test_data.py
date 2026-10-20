import pandas as pd
import pytest

from src.data import RAW_COLUMNS, clean_dataset


def test_clean_dataset_maps_severity_and_retains_missing_features():
    row = [63, 1, 1, 145, 233, 1, 2, 150, 0, 2.3, 3, "?", 6, 2]
    negative_row = [55, 0, 2, 130, 250, 0, 0, 160, 0, 1.0, 2, 0, 3, 0]
    cleaned = clean_dataset(pd.DataFrame([row, negative_row]))

    assert cleaned.columns.tolist() == RAW_COLUMNS
    assert cleaned["target"].tolist() == [1, 0]
    assert pd.isna(cleaned.loc[0, "ca"])


def test_clean_dataset_rejects_incorrect_source_shape():
    with pytest.raises(ValueError, match="Expected 14"):
        clean_dataset(pd.DataFrame([[1, 2, 3]]))
