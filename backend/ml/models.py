"""Reusable preprocessing and model definitions.

Price categories (Budget < ₹50k, Mid-range < ₹90k, Premium otherwise) are
project-defined labels rather than market-standard labels.
"""
from math import sqrt

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

NUMERIC_FEATURES = ["ram_gb", "storage_gb", "processor_score", "gpu_score", "screen_size", "rating"]
CATEGORICAL_FEATURES = ["brand"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def price_category(price):
    if price < 50000:
        return "Budget"
    if price < 90000:
        return "Mid-range"
    return "Premium"


def preprocessing():
    numeric = Pipeline([("imputer", SimpleImputer(strategy="median")), ("scale", StandardScaler())])
    categorical = Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("encode", OneHotEncoder(handle_unknown="ignore"))])
    return ColumnTransformer([("numeric", numeric, NUMERIC_FEATURES), ("categorical", categorical, CATEGORICAL_FEATURES)])


def price_pipeline(model=None):
    return Pipeline([("preprocess", preprocessing()), ("model", model if model is not None else LinearRegression())])


def classification_pipeline():
    return Pipeline([("preprocess", preprocessing()), ("model", LogisticRegression(max_iter=1000))])


def regression_metrics(model, x_test, y_test):
    predicted = model.predict(x_test)
    return {"mae": round(float(mean_absolute_error(y_test, predicted)), 2),
            "rmse": round(float(sqrt(mean_squared_error(y_test, predicted))), 2),
            "r2": round(float(r2_score(y_test, predicted)), 3)}


def comparison_model():
    """Optional tree-based comparison; it is not assumed to be superior."""
    return price_pipeline(RandomForestRegressor(n_estimators=150, random_state=42))
