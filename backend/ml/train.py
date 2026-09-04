"""Train and persist ML models per data source."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

try:
    from datasets import load_dataset, normalize_source_key, source_label
    from ml.models import (
        FEATURES,
        RECOMMENDATION_FEATURES,
        build_knn,
        classification_metrics,
        linear_regression_pipeline,
        price_category,
        price_category_thresholds,
        random_forest_classifier_pipeline,
        random_forest_regressor_pipeline,
        regression_metrics,
    )
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from datasets import load_dataset, normalize_source_key, source_label
    from ml.models import (
        FEATURES,
        RECOMMENDATION_FEATURES,
        build_knn,
        classification_metrics,
        linear_regression_pipeline,
        price_category,
        price_category_thresholds,
        random_forest_classifier_pipeline,
        random_forest_regressor_pipeline,
        regression_metrics,
    )

BASE = Path(__file__).resolve().parents[1]
MODEL_ROOT = Path(__file__).resolve().parent / "saved_models"
MIN_ROWS = 8
# Below this, models may still train/predict, but hold-out metrics are not reliable.
RELIABLE_ROWS = 25


def model_dir(source: str) -> Path:
    key = normalize_source_key(source)
    path = MODEL_ROOT / key
    path.mkdir(parents=True, exist_ok=True)
    return path


def prepare_training_frame(source: str = "kaggle") -> pd.DataFrame:
    data = load_dataset(source)
    if data.empty:
        raise ValueError("No laptop data is currently available for this source.")
    frame = data.copy()
    for column in ["price", "rating", "ram_gb", "storage_gb", "processor_score", "gpu_score", "screen_size"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame[frame["price"].notna() & (frame["price"] > 0)].copy()
    frame["brand"] = frame["brand"].fillna("Unknown").astype(str)
    # Impute sparse numeric features for training only (does not rewrite source CSV)
    for column in ["ram_gb", "storage_gb", "processor_score", "gpu_score", "screen_size", "rating"]:
        if frame[column].notna().any():
            frame[column] = frame[column].fillna(frame[column].median())
        else:
            defaults = {"ram_gb": 8, "storage_gb": 256, "processor_score": 4, "gpu_score": 1, "screen_size": 15.6, "rating": 3.5}
            frame[column] = defaults[column]
    frame = frame.drop_duplicates(subset=["title", "brand"], keep="first")
    if len(frame) < MIN_ROWS:
        raise ValueError(
            "There are not enough valid records to train this model. "
            "Please load a larger dataset or scrape more products."
        )
    return frame.reset_index(drop=True)


def train_models(source: str = "kaggle") -> dict:
    key = normalize_source_key(source)
    data = prepare_training_frame(key)
    x, y = data[FEATURES], data["price"]
    reliable = len(data) >= RELIABLE_ROWS
    test_size = 0.25 if len(data) >= 20 else 0.2
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=test_size, random_state=42)

    linear = linear_regression_pipeline().fit(x_train, y_train)
    forest = random_forest_regressor_pipeline().fit(x_train, y_train)
    linear_scores = regression_metrics(linear, x_test, y_test) if reliable else None
    forest_scores = regression_metrics(forest, x_test, y_test) if reliable else None

    low, high = price_category_thresholds(y)
    labels = y.map(lambda price: price_category(price, low, high))
    classifier = random_forest_classifier_pipeline().fit(x_train, labels.loc[x_train.index])
    class_scores = classification_metrics(classifier, x_test, labels.loc[x_test.index]) if reliable else None

    knn_payload = build_knn(data.assign(**{c: data[c] for c in RECOMMENDATION_FEATURES}), n_neighbors=min(5, len(data)))

    directory = model_dir(key)
    joblib.dump(linear, directory / "linear_regression.pkl")
    joblib.dump(forest, directory / "random_forest_regressor.pkl")
    joblib.dump(classifier, directory / "random_forest_classifier.pkl")
    joblib.dump(knn_payload, directory / "knn_recommender.pkl")
    joblib.dump(data, directory / "training_frame.pkl")

    reliability_note = None
    if not reliable:
        reliability_note = (
            f"There are only {len(data)} valid records for {source_label(key)}. "
            "Predictions and recommendations still use this real data, but MAE / RMSE / R² "
            f"and classification scores are not shown until at least {RELIABLE_ROWS} records "
            "are available for a more reliable evaluation."
        )

    if reliable:
        best = "Random Forest Regressor" if forest_scores["rmse"] <= linear_scores["rmse"] else "Linear Regression"
    else:
        best = None

    metrics = {
        "source": key,
        "dataset_source": source_label(key),
        "rows": len(data),
        "training_rows": len(x_train),
        "testing_rows": len(x_test),
        "features": FEATURES,
        "reliable": reliable,
        "reliability_note": reliability_note,
        "min_rows_for_metrics": RELIABLE_ROWS,
        "category_thresholds": {"budget_max": round(low, 2), "mid_max": round(high, 2)},
        "linear_regression": linear_scores,
        "random_forest": forest_scores,
        "random_forest_regressor": forest_scores,
        "classification": class_scores,
        "random_forest_classifier": class_scores,
        "recommendation": {
            "algorithm": "K-Nearest Neighbors",
            "neighbors": knn_payload["model"].n_neighbors,
            "features": RECOMMENDATION_FEATURES,
            "note": "Recommendations return the nearest real laptops from the active source using Euclidean distance on scaled features.",
        },
        "best_model": best,
        "last_trained": datetime.now(timezone.utc).isoformat(),
        "actual_vs_predicted": [
            {"actual": round(float(a), 2), "predicted": round(float(p), 2)}
            for a, p in zip(y_test.tolist(), forest.predict(x_test).tolist())
        ][:40] if reliable else [],
        "algorithms": [
            {"name": "Linear Regression", "purpose": "Price Prediction"},
            {"name": "Random Forest Regressor", "purpose": "Price Prediction"},
            {"name": "Random Forest Classifier", "purpose": "Classification"},
            {"name": "KNN", "purpose": "Recommendation"},
        ],
    }
    (directory / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


def load_model(source: str, name: str):
    path = model_dir(source) / name
    if not path.exists():
        train_models(source)
    path = model_dir(source) / name
    if not path.exists():
        raise FileNotFoundError(
            "Not enough valid data is available for this ML operation."
        )
    return joblib.load(path)


def load_metrics(source: str) -> dict:
    path = model_dir(source) / "metrics.json"
    if not path.exists():
        return train_models(source)
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_trained(source: str) -> dict:
    directory = model_dir(source)
    needed = (
        "linear_regression.pkl",
        "random_forest_regressor.pkl",
        "random_forest_classifier.pkl",
        "knn_recommender.pkl",
        "metrics.json",
    )
    if all((directory / name).exists() for name in needed):
        metrics = load_metrics(source)
        # Refresh older metrics files that predate the reliability flag
        if "reliable" not in metrics:
            return train_models(source)
        return metrics
    return train_models(source)


if __name__ == "__main__":
    print(json.dumps(train_models("kaggle"), indent=2))
