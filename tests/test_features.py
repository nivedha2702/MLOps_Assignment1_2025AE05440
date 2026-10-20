import numpy as np
import pandas as pd

from src.features import FEATURE_NAMES, build_pipeline


def sample_frame(size=24):
    data = {name: np.arange(size) % 4 for name in FEATURE_NAMES}
    data.update(
        {
            "age": np.linspace(35, 75, size),
            "trestbps": np.linspace(105, 180, size),
            "chol": np.linspace(160, 320, size),
            "thalach": np.linspace(100, 190, size),
            "oldpeak": np.linspace(0, 4, size),
            "target": [index % 2 for index in range(size)],
        }
    )
    frame = pd.DataFrame(data)
    frame.loc[0, "ca"] = np.nan
    return frame


def test_both_pipeline_variants_fit_and_return_probabilities():
    data = sample_frame()
    x = data[FEATURE_NAMES]
    y = data["target"]
    for name in ("logistic_regression", "random_forest"):
        pipeline = build_pipeline(name).fit(x, y)
        probabilities = pipeline.predict_proba(x)
        assert probabilities.shape == (len(data), 2)
        assert np.allclose(probabilities.sum(axis=1), 1)
        assert set(pipeline.predict(x)).issubset({0, 1})
