"""Flask API for laptop data, model inference, and recommendations."""
import logging
from pathlib import Path

import joblib
import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS

from ml.models import FEATURES
from ml.recommender import recommend_laptops
from scraper.scraper import scrape_stored_products

BASE = Path(__file__).resolve().parent
DATA_PATH, MODEL_DIR = BASE / "data" / "laptops.csv", BASE / "ml" / "saved_models"
app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)


def dataset():
    if not DATA_PATH.exists():
        raise FileNotFoundError("Dataset is unavailable. Run scraping or provide backend/data/laptops.csv.")
    return pd.read_csv(DATA_PATH).fillna(0)


def input_features(payload):
    if not isinstance(payload, dict):
        raise ValueError("A JSON object is required.")
    missing = [key for key in FEATURES if key not in payload and key != "brand"]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")
    values = {key: payload.get(key, "Unknown") if key == "brand" else payload[key] for key in FEATURES}
    for key in FEATURES[:-1]:
        values[key] = float(values[key])
    return pd.DataFrame([values])


def model(name):
    path = MODEL_DIR / name
    if not path.exists():
        raise FileNotFoundError("Model files are missing. Run `python ml/train.py` first.")
    return joblib.load(path)


@app.errorhandler(Exception)
def handle_error(error):
    status = 400 if isinstance(error, ValueError) else 404 if isinstance(error, FileNotFoundError) else 500
    app.logger.exception("API error: %s", error)
    if status == 500:
        return jsonify(error="The server could not complete this request."), status
    return jsonify(error=str(error)), status


@app.get("/api/laptops")
def laptops():
    records = dataset().reset_index(names="id").to_dict("records")
    return jsonify(records)


@app.get("/api/laptops/<int:laptop_id>")
def laptop(laptop_id):
    data = dataset().reset_index(names="id")
    match = data[data["id"] == laptop_id]
    if match.empty:
        return jsonify(error="Laptop not found"), 404
    return jsonify(match.iloc[0].to_dict())


@app.post("/api/predict-price")
def predict_price():
    prediction = model("price_model.pkl").predict(input_features(request.get_json()))[0]
    return jsonify(predicted_price=round(max(0, float(prediction)), 2), model="Linear Regression")


@app.post("/api/classify")
def classify():
    trained = model("classification_model.pkl")
    features = input_features(request.get_json())
    category = trained.predict(features)[0]
    response = {"category": category, "model": "Logistic Regression"}
    if hasattr(trained, "predict_proba"):
        response["probability"] = round(float(max(trained.predict_proba(features)[0])), 3)
    return jsonify(response)


@app.post("/api/recommend")
def recommend():
    payload = request.get_json() or {}
    for required in ("ram_gb", "storage_gb", "budget"):
        if required not in payload:
            raise ValueError(f"Missing required field: {required}")
    return jsonify(recommend_laptops(dataset(), payload))


@app.get("/api/stats")
def stats():
    data = dataset()
    prices = pd.to_numeric(data["price"], errors="coerce").dropna()
    return jsonify(count=len(data), average_price=round(float(prices.mean()), 2), minimum_price=float(prices.min()), maximum_price=float(prices.max()), average_rating=round(float(pd.to_numeric(data["rating"], errors="coerce").mean()), 2), brands=sorted(data["brand"].astype(str).unique().tolist()))


@app.post("/api/scrape")
def scrape():
    """Scrape only Amazon product URLs already stored in the catalog CSV."""
    try:
        summary = scrape_stored_products()
    except (OSError, ValueError) as error:
        app.logger.warning("Scrape unavailable: %s", error)
        return jsonify(success=False, message="Scraping failed", error="Stored Amazon URLs could not be processed."), 503
    return jsonify(summary), 200 if summary["success"] or summary["total_urls"] == 0 else 503


if __name__ == "__main__":
    app.run(port=5000)
