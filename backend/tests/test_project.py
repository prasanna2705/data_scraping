"""Backend tests for dataset loading, scraping resolution, ML, and APIs."""
from __future__ import annotations

import pandas as pd
import pytest

from app import app
from datasets import load_dataset, normalize_source_key, save_dataset
from ml.recommender import recommend_laptops
from ml.train import train_models
from scraper import scraper
from scraper.resolver import resolve_query
from scraper.base import ComingSoonError, UnsupportedSourceError
from utils.feature_extraction import clean_price, clean_rating, extract_features
from utils.normalize import clean_dataframe, dedupe_records, normalize_record


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


def test_kaggle_dataset_loads_with_required_columns():
    data = load_dataset("kaggle")
    assert len(data) >= 1000
    for column in ("title", "price", "brand", "ram_gb", "storage_gb", "source"):
        assert column in data.columns
    assert set(data["source"].dropna().unique()) == {"Kaggle"}


def test_cleaning_and_feature_extraction():
    item = extract_features(
        "ASUS Gaming Ryzen 7 16GB RAM 512GB SSD RTX 4060 15.6 inch",
        "₹89,990",
        "4.3 out of 5 stars",
    )
    assert clean_price("₹54,990") == 54990
    assert clean_rating("4.3 out of 5 stars") == 4.3
    assert item["ram_gb"] == 16 and item["storage_gb"] == 512 and item["gpu_score"] == 7


def test_normalize_and_dedupe():
    records = [
        normalize_record({"title": "Dell 16GB RAM 512GB SSD", "price": "₹79,999", "brand": "Dell"}, "Amazon"),
        normalize_record({"title": "Dell 16GB RAM 512GB SSD", "price": "79999", "brand": "Dell", "product_url": "https://www.amazon.in/dp/B012345678"}, "Amazon"),
        normalize_record({"title": "HP 8GB RAM 256GB SSD", "price": "49999", "brand": "HP", "asin": "B0ABCDEF12"}, "Amazon"),
    ]
    unique, duplicates = dedupe_records(records)
    assert duplicates >= 1
    assert len(unique) >= 2
    frame, stats = clean_dataframe(pd.DataFrame(records), "Amazon")
    assert stats["valid_products"] >= 1
    assert not frame.empty


def test_source_detection_and_url_validation():
    amazon = resolve_query("Amazon laptops")
    assert amazon["source_key"] == "amazon" and "amazon.in" in amazon["url"]
    # Company name should not pollute the retail search query
    assert "k=laptops" in amazon["url"] or "k=laptop" in amazon["url"]
    assert "Amazon+laptops" not in amazon["url"]
    with pytest.raises(ComingSoonError):
        resolve_query("https://www.flipkart.com/")
    with pytest.raises(ComingSoonError):
        resolve_query("OnePlus")
    with pytest.raises(UnsupportedSourceError):
        resolve_query("https://www.unsupported-laptop-shop.example/")


def test_coming_soon_scrape_api(client):
    response = client.post("/api/scrape", json={"query": "Flipkart laptops"})
    assert response.status_code == 200
    assert response.json["success"] is False
    assert "coming soon" in response.json["message"].casefold()


def test_amazon_catalog_isolated_from_kaggle(client):
    amazon = load_dataset("amazon")
    kaggle = load_dataset("kaggle")
    assert len(kaggle) >= 1000
    if amazon.empty:
        catalog = client.get("/api/catalog?source=amazon")
        assert catalog.status_code == 200
        assert catalog.json["total"] == 0
        assert "No laptop data" in (catalog.json.get("message") or "")
    else:
        assert all(str(value) == "Amazon" for value in amazon["source"].dropna())
        catalog = client.get("/api/catalog?source=amazon&per_page=5")
        assert catalog.status_code == 200 and catalog.json["total"] == len(amazon)
        predict = client.post("/api/predict-price", json={
            "source": "amazon",
            "brand": "HP",
            "ram_gb": 16,
            "storage_gb": 512,
            "processor": "Intel Core i5",
            "gpu": "Intel UHD",
            "screen_size": 15.6,
            "rating": 4.1,
        })
        assert predict.status_code == 200
        assert predict.json["linear_regression"]["predicted_price"] > 0
        assert predict.json["source"] == "amazon"


def test_product_extraction_uses_fallbacks():
    html = '''<script type="application/ld+json">{"@type":"Product","name":"ASUS Test Laptop Ryzen 7 16GB RAM 512GB SSD RTX 4060 15.6 inch","offers":{"price":"89990","availability":"InStock"},"aggregateRating":{"ratingValue":"4.4"}}</script><img id="landingImage" src="https://images.example/test.jpg">'''
    product = scraper.extract_product(html, "https://www.amazon.in/dp/B012345678")
    assert product["asin"] == "B012345678" and product["price"] == 89990
    assert product["rating"] == 4.4 and product["image_url"] == "https://images.example/test.jpg"


def test_upsert_updates_asin_without_duplicates(monkeypatch):
    saved = []
    monkeypatch.setattr(scraper, "_read_rows", lambda *_: [{"asin": "B012345678", "product_url": "https://www.amazon.in/dp/B012345678", "title": "Old"}])
    monkeypatch.setattr(scraper, "save_rows", lambda rows, *_: saved.extend(rows))
    inserted, updated = scraper.upsert_products([{
        "asin": "B012345678",
        "product_url": "https://www.amazon.in/dp/B012345678",
        "title": "New",
    }])
    assert (inserted, updated) == (0, 1) and len(saved) == 1 and saved[0]["title"] == "New"


def test_scrape_api_rejects_empty_and_unsupported(client):
    empty = client.post("/api/scrape", json={})
    assert empty.status_code == 400
    unsupported = client.post("/api/scrape", json={"query": "https://www.example-shop.test/laptops"})
    assert unsupported.status_code == 200
    assert unsupported.json["success"] is False
    assert "not currently supported" in unsupported.json["message"].lower() or "supported" in unsupported.json["message"].lower()


def test_catalog_predict_classify_recommend_ml(client):
    train_models("kaggle")
    catalog = client.get("/api/catalog?source=kaggle&per_page=5")
    assert catalog.status_code == 200 and catalog.json["total"] >= 1000
    assert catalog.json["records"]

    payload = {
        "source": "kaggle",
        "brand": "ASUS",
        "ram_gb": 16,
        "storage_gb": 512,
        "processor": "Intel Core i7",
        "gpu": "NVIDIA RTX 4050",
        "screen_size": 15.6,
        "rating": 4.3,
        "budget": 90000,
    }
    predict = client.post("/api/predict-price", json=payload)
    assert predict.status_code == 200
    assert predict.json["linear_regression"]["predicted_price"] > 0
    assert predict.json["random_forest"]["predicted_price"] > 0

    classify = client.post("/api/classify", json=payload)
    assert classify.status_code == 200
    assert classify.json["category"] in {"Budget", "Mid Range", "Premium"}

    recommend = client.post("/api/recommend", json=payload)
    assert recommend.status_code == 200
    assert isinstance(recommend.json["recommendations"], list)
    assert len(recommend.json["recommendations"]) >= 1

    analysis = client.get("/api/ml-analysis?source=kaggle")
    assert analysis.status_code == 200
    assert "linear_regression" in analysis.json
    assert "classification" in analysis.json
    assert analysis.json["recommendation"]["algorithm"] == "K-Nearest Neighbors"


def test_source_isolation(tmp_path, monkeypatch):
    # Ensure Amazon catalog never reads Kaggle rows
    kaggle = load_dataset("kaggle")
    amazon = load_dataset("amazon")
    assert len(kaggle) > 0
    assert all(str(value) == "Kaggle" for value in kaggle["source"].dropna())
    if not amazon.empty:
        assert all(str(value) == "Amazon" for value in amazon["source"].dropna())


def test_recommendations_knn_unit():
    data = pd.DataFrame([{
        "title": "One", "brand": "HP", "price": 50000, "rating": 4.2,
        "ram_gb": 16, "storage_gb": 512, "processor_score": 5, "gpu_score": 0, "screen_size": 15.6,
    }])
    assert recommend_laptops(data, {"ram_gb": 16, "storage_gb": 512, "budget": 60000}, source="kaggle")[0]["title"] == "One"


def test_normalize_source_key():
    assert normalize_source_key("Amazon") == "amazon"
    assert normalize_source_key("Kaggle") == "kaggle"
