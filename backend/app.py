"""Flask API for Laptop Intelligence — scraping, catalog, and ML by source."""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException
from flask_cors import CORS

from datasets import is_active_source, list_sources, load_dataset, normalize_source_key, source_label, source_path
from ml.models import FEATURES, feature_names
from ml.recommender import recommend_laptops
from ml.train import ensure_trained, load_metrics, load_model, train_models
from scraper.manager import run_scrape, validate_source
from utils.feature_extraction import normalize_payload
from utils.schema import ACTIVE_SOURCE_KEYS, COMING_SOON_SOURCES

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)


def request_source(default: str = "kaggle") -> str:
    payload = request.get_json(silent=True) or {}
    raw = (
        payload.get("source")
        or request.args.get("source")
        or default
    )
    return normalize_source_key(raw)


def input_features(payload: dict) -> pd.DataFrame:
    if not isinstance(payload, dict):
        raise ValueError("A JSON object is required.")
    values = normalize_payload(payload)
    missing = [key for key in ("ram_gb", "storage_gb", "screen_size") if values.get(key) is None]
    if missing:
        raise ValueError(f"Please provide valid values for: {', '.join(missing)}.")
    rating = values.get("rating")
    if rating is None:
        values["rating"] = 3.5
    elif not 0 <= values["rating"] <= 5:
        raise ValueError("Rating must be between 0 and 5.")
    return pd.DataFrame([{
        key: values.get(key, "Unknown") if key == "brand" else values.get(key, 0)
        for key in FEATURES
    }])


@app.errorhandler(Exception)
def handle_error(error):
    if isinstance(error, HTTPException):
        return jsonify(error=error.description), error.code

    if isinstance(error, ValueError):
        return jsonify(error=str(error)), 400

    app.logger.exception("API error: %s", error)
    return jsonify(
        error="The server could not complete this request. Please try again later."
    ), 500

@app.get("/api/health")
def health():
    return jsonify(status="ok")


@app.get("/api/sources")
def sources():
    return jsonify(sources=list_sources())


@app.get("/api/datasets/kaggle")
def datasets_kaggle():
    data = load_dataset("kaggle")
    return jsonify(
        source="kaggle",
        label=source_label("kaggle"),
        records=len(data),
        path=str(source_path("kaggle")),
        columns=list(data.columns) if not data.empty else [],
        sample=data.head(5).replace({np.nan: None}).to_dict("records"),
    )


@app.post("/api/datasets/select")
def select_dataset():
    source = request_source()
    if source in COMING_SOON_SOURCES:
        return jsonify(
            source=source,
            label=source_label(source),
            records=0,
            trained=False,
            coming_soon=True,
            message=f"{source_label(source)} is Coming Soon. Currently available sources: Kaggle and Amazon.",
        )
    if not is_active_source(source):
        return jsonify(
            source=source,
            label=source_label(source),
            records=0,
            trained=False,
            message=f"Unknown or unavailable source. Currently available: {', '.join(ACTIVE_SOURCE_KEYS)}.",
        ), 400
    data = load_dataset(source)
    if data.empty:
        return jsonify(
            source=source,
            label=source_label(source),
            records=0,
            trained=False,
            message="No laptop data is currently available for this source.",
        )
    # Eagerly train so downstream pages are ready
    try:
        metrics = ensure_trained(source)
        trained = True
        train_message = "Models ready for this source."
        if metrics and metrics.get("reliability_note"):
            train_message = metrics["reliability_note"]
    except ValueError as exc:
        metrics = None
        trained = False
        train_message = str(exc)
    return jsonify(
        source=source,
        label=source_label(source),
        records=len(data),
        trained=trained,
        train_message=train_message,
        metrics=metrics,
        reliable=bool(metrics.get("reliable")) if metrics else False,
        message=f"Active source set to {source_label(source)}.",
    )


@app.get("/api/catalog")
@app.get("/api/laptops")
def catalog():
    source = request_source()
    data = load_dataset(source)
    if data.empty:
        return jsonify(
            records=[], total=0, page=1, per_page=12, brands=[], processors=[],
            source=source, label=source_label(source),
            message="No laptop data is currently available for this source.",
        )

    query = request.args.get("search", "").casefold()
    brand = request.args.get("brand", "")
    processor = request.args.get("processor", "")

    for column in ("min_price", "max_price", "ram_gb", "storage_gb", "min_rating"):
        value = request.args.get(column, type=float)
        if value is None or data.empty:
            continue
        numeric = pd.to_numeric(data.get(column.replace("min_", "").replace("max_", ""), data.get(column)), errors="coerce")
        if column == "min_price":
            data = data[pd.to_numeric(data["price"], errors="coerce") >= value]
        elif column == "max_price":
            data = data[pd.to_numeric(data["price"], errors="coerce") <= value]
        elif column == "min_rating":
            data = data[pd.to_numeric(data["rating"], errors="coerce") >= value]
        else:
            data = data[pd.to_numeric(data[column], errors="coerce") == value]

    if query and "title" in data:
        data = data[data.title.astype(str).str.casefold().str.contains(query, na=False)]
    if brand and "brand" in data:
        data = data[data.brand.astype(str).str.casefold() == brand.casefold()]
    if processor and "processor" in data:
        data = data[data.processor.astype(str).str.casefold().str.contains(processor.casefold(), na=False)]

    sort = request.args.get("sort", "price_asc")
    if sort == "rating_desc":
        key, ascending = "rating", False
    elif sort == "price_desc":
        key, ascending = "price", False
    else:
        key, ascending = "price", True
    if key in data:
        data = data.sort_values(key, ascending=ascending, na_position="last")

    page = max(1, request.args.get("page", 1, type=int))
    per_page = min(100, max(1, request.args.get("per_page", 12, type=int)))
    total = len(data)
    full = load_dataset(source)
    brands = sorted(full.get("brand", pd.Series(dtype=str)).dropna().astype(str).unique().tolist())
    processors = sorted({
        str(value).split()[0] + " " + str(value).split()[1] if len(str(value).split()) >= 2 else str(value)
        for value in full.get("processor", pd.Series(dtype=str)).dropna().astype(str).tolist()
        if str(value).strip()
    })
    records = data.iloc[(page - 1) * per_page: page * per_page].reset_index(names="id").replace({np.nan: None}).to_dict("records")
    return jsonify(
        records=records, total=total, page=page, per_page=per_page,
        brands=brands, processors=processors[:40],
        source=source, label=source_label(source),
    )


@app.get("/api/laptops/<int:laptop_id>")
def laptop_detail(laptop_id: int):
    source = request_source()
    data = load_dataset(source).reset_index(names="id")
    match = data[data.id == laptop_id]
    if match.empty:
        return jsonify(error="Laptop not found"), 404
    return jsonify(match.iloc[0].replace({np.nan: None}).to_dict())


@app.get("/api/stats")
def stats():
    source = request_source()
    data = load_dataset(source)
    prices = pd.to_numeric(data.get("price", pd.Series(dtype=float)), errors="coerce").dropna()
    if prices.empty:
        return jsonify(
            source=source, label=source_label(source), count=0,
            average_price=None, minimum_price=None, maximum_price=None,
            average_rating=None, brands=[],
            message="No laptop data is currently available for this source.",
        )
    rating = pd.to_numeric(data.get("rating", pd.Series(dtype=float)), errors="coerce")
    return jsonify(
        source=source, label=source_label(source), count=len(data),
        average_price=round(float(prices.mean()), 2),
        minimum_price=float(prices.min()),
        maximum_price=float(prices.max()),
        average_rating=round(float(rating.mean()), 2) if rating.notna().any() else None,
        brands=sorted(data.brand.dropna().astype(str).unique().tolist()),
        most_expensive=data.loc[prices.idxmax(), "title"],
        lowest_priced=data.loc[prices.idxmin(), "title"],
        most_popular_brand=data.brand.mode().iat[0] if not data.brand.mode().empty else None,
    )


@app.post("/api/scrape")
def scrape():
    payload = request.get_json(silent=True) or {}
    query = payload.get("query") or payload.get("url") or payload.get("website") or ""
    if not str(query).strip():
        return jsonify(
            success=False, status="Failed", records_found=0,
            message="Please enter a valid website URL or supported company/source name.",
        ), 400
    result = run_scrape(str(query).strip(), max_products=int(payload.get("max_products", 48) or 48))
    if result.get("success"):
        try:
            ensure_trained(result["source_key"])
            result["models_trained"] = True
        except ValueError as exc:
            result["models_trained"] = False
            result["train_message"] = str(exc)
    status = 200 if result.get("success") else 200
    return jsonify(result), status


@app.post("/api/sources/validate")
def validate():
    payload = request.get_json(silent=True) or {}
    return jsonify(validate_source(payload.get("url") or payload.get("query") or ""))


@app.post("/api/predict-price")
def predict_price():
    payload = request.get_json(silent=True) or {}
    source = normalize_source_key(payload.get("source", "kaggle"))
    data = load_dataset(source)
    if data.empty:
        raise ValueError("No laptop data is currently available for this source.")
    try:
        ensure_trained(source)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc
    features = input_features(payload)
    linear = load_model(source, "linear_regression.pkl")
    forest = load_model(source, "random_forest_regressor.pkl")
    linear_pred = float(linear.predict(features)[0])
    forest_pred = float(forest.predict(features)[0])
    metrics = load_metrics(source)
    return jsonify(
        source=source,
        label=source_label(source),
        reliable=metrics.get("reliable", True),
        reliability_note=metrics.get("reliability_note"),
        linear_regression={
            "predicted_price": round(max(0, linear_pred), 2),
            "metrics": metrics.get("linear_regression"),
        },
        random_forest={
            "predicted_price": round(max(0, forest_pred), 2),
            "metrics": metrics.get("random_forest"),
        },
        predicted_price=round(max(0, forest_pred), 2),
        model="Random Forest Regressor",
        best_model=metrics.get("best_model"),
    )


@app.post("/api/classify")
def classify():
    payload = request.get_json(silent=True) or {}
    source = normalize_source_key(payload.get("source", "kaggle"))
    if load_dataset(source).empty:
        raise ValueError("No laptop data is currently available for this source.")
    try:
        ensure_trained(source)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc
    features = input_features(payload)
    model = load_model(source, "random_forest_classifier.pkl")
    category = model.predict(features)[0]
    response = {
        "source": source,
        "label": source_label(source),
        "category": category,
        "model": "Random Forest Classifier",
    }
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(features)[0]
        classes = list(model.classes_)
        response["probability"] = round(float(max(proba)), 3)
        response["probabilities"] = {
            str(label): round(float(score), 3) for label, score in zip(classes, proba)
        }
    metrics = load_metrics(source)
    response["metrics"] = metrics.get("classification")
    response["thresholds"] = metrics.get("category_thresholds")
    response["reliable"] = metrics.get("reliable", True)
    response["reliability_note"] = metrics.get("reliability_note")
    return jsonify(response)


@app.post("/api/recommend")
def recommend():
    payload = request.get_json(silent=True) or {}
    source = normalize_source_key(payload.get("source", "kaggle"))
    for required in ("ram_gb", "storage_gb", "budget"):
        if required not in payload:
            raise ValueError(f"Missing required field: {required}")
    data = load_dataset(source)
    if data.empty:
        raise ValueError("No laptop data is currently available for this source.")
    try:
        ensure_trained(source)
    except ValueError:
        pass
    results = recommend_laptops(data, normalize_payload(payload), limit=int(payload.get("limit", 5) or 5), source=source)
    return jsonify(
        source=source,
        label=source_label(source),
        recommendations=results,
        # backward compatible list root consumers
        items=results,
        count=len(results),
        message=None if results else "No current catalog listings meet those requirements.",
    )


@app.get("/api/ml-analysis")
@app.get("/api/model-performance")
def ml_analysis():
    source = request_source()
    if load_dataset(source).empty:
        return jsonify(
            source=source, label=source_label(source),
            error="No laptop data is currently available for this source.",
            algorithms=[],
        ), 200
    try:
        metrics = ensure_trained(source)
    except ValueError as exc:
        return jsonify(source=source, label=source_label(source), error=str(exc), algorithms=[]), 200
    return jsonify(metrics)


@app.post("/api/train")
def train():
    source = request_source()
    return jsonify(train_models(source))


@app.get("/api/feature-importance")
def importance():
    source = request_source()
    try:
        ensure_trained(source)
        trained = load_model(source, "random_forest_regressor.pkl")
    except ValueError as exc:
        return jsonify(items=[], error=str(exc))
    estimator = trained.named_steps["model"]
    if not hasattr(estimator, "feature_importances_"):
        return jsonify(items=[])
    return jsonify(items=[
        {"feature": str(name), "importance": round(float(value), 4)}
        for name, value in sorted(
            zip(feature_names(trained), estimator.feature_importances_),
            key=lambda item: item[1],
            reverse=True,
        )
    ])


@app.get("/api/data-quality")
def data_quality():
    source = request_source()
    raw = load_dataset(source)
    required = ["title", "price", "ram_gb", "storage_gb"]
    missing = int(raw[required].isna().sum().sum()) if not raw.empty and set(required).issubset(raw) else 0
    identity = [c for c in ("asin", "product_url", "title", "brand") if c in raw]
    duplicates = int(raw.duplicated(subset=identity, keep="first").sum()) if identity and not raw.empty else 0
    invalid = int((pd.to_numeric(raw.get("price", pd.Series(dtype=float)), errors="coerce") <= 0).sum()) if not raw.empty else 0
    return jsonify(
        source=source, label=source_label(source),
        total_records=len(raw),
        clean_records=max(0, len(raw) - duplicates - invalid),
        catalog_records=len(raw),
        duplicates=duplicates,
        missing_values=missing,
        invalid_records=invalid,
        features_extracted=len(FEATURES),
        data_sources=[source_label(source)] if len(raw) else [],
    )
@app.get("/")
def home():
    return jsonify(
        status="ok",
        message="Laptop Intelligence API is running"
    )

@app.get("/api/analytics")
def analytics():
    source = request_source()
    data = load_dataset(source)
    if data.empty:
        return jsonify(source=source, price_distribution=[], brand_prices=[], ram_prices=[])
    clean = data.copy()
    for column in ("price", "ram_gb", "processor_score", "gpu_score", "rating"):
        clean[column] = pd.to_numeric(clean.get(column), errors="coerce")
    return jsonify(
        source=source,
        price_distribution=clean[["title", "price"]].dropna().head(200).to_dict("records"),
        brand_prices=clean.groupby("brand", dropna=True).price.mean().round(2).reset_index().to_dict("records"),
        ram_prices=clean.groupby("ram_gb").price.mean().round(2).reset_index().to_dict("records"),
    )


if __name__ == "__main__":
    app.run(port=5000, debug=False, use_reloader=False)
