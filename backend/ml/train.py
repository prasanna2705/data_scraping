"""Train and persist models once, outside API request handling."""
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.model_selection import train_test_split

try:  # Supports both `python ml/train.py` and `python -m ml.train`.
    from ml.models import FEATURES, classification_pipeline, comparison_model, price_category, price_pipeline, regression_metrics
except ModuleNotFoundError:
    from models import FEATURES, classification_pipeline, comparison_model, price_category, price_pipeline, regression_metrics

BASE = Path(__file__).resolve().parents[1]
DATA_PATH = BASE / "data" / "laptops.csv"
MODEL_DIR = Path(__file__).resolve().parent / "saved_models"


def load_and_clean(path=DATA_PATH):
    if not Path(path).exists():
        raise FileNotFoundError(f"Dataset not found: {path}. Run the scraper or copy the labelled development sample first.")
    data = pd.read_csv(path)
    required = {"title", "price", "rating", *FEATURES}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {', '.join(sorted(missing))}")
    data = data.drop_duplicates(subset="title").copy()
    for column in ["price", "rating", "ram_gb", "storage_gb", "processor_score", "gpu_score", "screen_size"]:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    data = data[data["price"].notna() & (data["price"] > 0)]
    data["brand"] = data["brand"].fillna("Unknown")
    return data


def train_models(path=DATA_PATH):
    data = load_and_clean(path)
    if len(data) < 12:
        raise ValueError("At least 12 priced rows are required to train meaningful demonstration models.")
    x, y = data[FEATURES], data["price"]
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.25, random_state=42)
    price_model = price_pipeline().fit(x_train, y_train)
    forest = comparison_model().fit(x_train, y_train)
    labels = y.map(price_category)
    class_model = classification_pipeline().fit(x_train, labels.loc[x_train.index])
    MODEL_DIR.mkdir(exist_ok=True)
    joblib.dump(price_model, MODEL_DIR / "price_model.pkl")
    joblib.dump(class_model, MODEL_DIR / "classification_model.pkl")
    metrics = {"linear_regression": regression_metrics(price_model, x_test, y_test), "random_forest_comparison": regression_metrics(forest, x_test, y_test), "rows": len(data)}
    (MODEL_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


if __name__ == "__main__":
    print(json.dumps(train_models(), indent=2))
