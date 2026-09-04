"""Four ML algorithms: Linear Regression, RF Regressor, RF Classifier, KNN."""
from __future__ import annotations

from math import sqrt

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)
from sklearn.neighbors import NearestNeighbors
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

NUMERIC_FEATURES = ["ram_gb", "storage_gb", "processor_score", "gpu_score", "screen_size", "rating"]
CATEGORICAL_FEATURES = ["brand"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
RECOMMENDATION_FEATURES = [
    "ram_gb", "storage_gb", "processor_score", "gpu_score", "screen_size", "rating", "price",
]


def price_category_thresholds(prices) -> tuple[float, float]:
    """Derive Budget / Mid Range / Premium cuts from the active dataset."""
    series = np.asarray(prices, dtype=float)
    series = series[np.isfinite(series)]
    if len(series) < 3:
        return 50000.0, 90000.0
    low, high = np.percentile(series, [33.33, 66.66])
    if low >= high:
        return float(np.median(series) * 0.75), float(np.median(series) * 1.25)
    return float(low), float(high)


def price_category(price, low: float, high: float) -> str:
    value = float(price)
    if value < low:
        return "Budget"
    if value < high:
        return "Mid Range"
    return "Premium"


def preprocessing():
    numeric = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
    ])
    categorical = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("encode", OneHotEncoder(handle_unknown="ignore")),
    ])
    return ColumnTransformer([
        ("numeric", numeric, NUMERIC_FEATURES),
        ("categorical", categorical, CATEGORICAL_FEATURES),
    ])


def linear_regression_pipeline():
    return Pipeline([("preprocess", preprocessing()), ("model", LinearRegression())])


def random_forest_regressor_pipeline():
    return Pipeline([
        ("preprocess", preprocessing()),
        ("model", RandomForestRegressor(n_estimators=150, random_state=42)),
    ])


def random_forest_classifier_pipeline():
    return Pipeline([
        ("preprocess", preprocessing()),
        ("model", RandomForestClassifier(n_estimators=150, random_state=42)),
    ])


def regression_metrics(model, x_test, y_test):
    predicted = model.predict(x_test)
    return {
        "mae": round(float(mean_absolute_error(y_test, predicted)), 2),
        "rmse": round(float(sqrt(mean_squared_error(y_test, predicted))), 2),
        "r2": round(float(r2_score(y_test, predicted)), 3),
    }


def classification_metrics(model, x_test, y_test):
    predicted = model.predict(x_test)
    return {
        "accuracy": round(float(accuracy_score(y_test, predicted)), 3),
        "precision": round(float(precision_score(y_test, predicted, average="weighted", zero_division=0)), 3),
        "recall": round(float(recall_score(y_test, predicted, average="weighted", zero_division=0)), 3),
        "f1": round(float(f1_score(y_test, predicted, average="weighted", zero_division=0)), 3),
    }


def feature_names(trained_pipeline):
    try:
        return trained_pipeline.named_steps["preprocess"].get_feature_names_out()
    except AttributeError:
        return FEATURES


def build_knn(frame, n_neighbors: int = 5):
    """Fit a KNN model on recommendation features from the active dataset."""
    data = frame.copy()
    for column in RECOMMENDATION_FEATURES:
        data[column] = data[column].astype(float)
    scaler = StandardScaler()
    matrix = scaler.fit_transform(data[RECOMMENDATION_FEATURES])
    neighbors = min(max(1, n_neighbors), len(data))
    model = NearestNeighbors(n_neighbors=neighbors, metric="euclidean")
    model.fit(matrix)
    return {"model": model, "scaler": scaler, "features": RECOMMENDATION_FEATURES, "index": data.index.tolist()}
