import pandas as pd

from app import app
from ml.recommender import recommend_laptops
from ml.train import train_models
from scraper import scraper
from utils.feature_extraction import clean_price, clean_rating, extract_features


def test_cleaning_and_feature_extraction():
    item = extract_features("ASUS Gaming Ryzen 7 16GB RAM 512GB SSD RTX 4060 15.6 inch", "₹89,990", "4.3 out of 5 stars")
    assert clean_price("₹54,990") == 54990 and clean_rating("4.3 out of 5 stars") == 4.3
    assert item["ram_gb"] == 16 and item["storage_gb"] == 512 and item["gpu_score"] == 7


def test_stored_url_scraper_returns_no_url_summary():
    summary = scraper.scrape_stored_products()
    assert summary["success"] is False and summary["message"] == "No Amazon URLs are available for scraping."


def test_product_extraction_uses_fallbacks():
    html = '''<script type="application/ld+json">{"@type":"Product","name":"ASUS Test Ryzen 7 16GB RAM 512GB SSD RTX 4060 15.6 inch","offers":{"price":"89990","availability":"InStock"},"aggregateRating":{"ratingValue":"4.4"}}</script><img id="landingImage" src="https://images.example/test.jpg">'''
    product = scraper.extract_product(html, "https://www.amazon.in/dp/B012345678")
    assert product["asin"] == "B012345678" and product["price"] == 89990
    assert product["rating"] == 4.4 and product["image_url"] == "https://images.example/test.jpg"


def test_batch_continues_after_one_url_failure(monkeypatch):
    urls = ["https://www.amazon.in/dp/B012345678", "https://example.com/not-amazon"]
    monkeypatch.setattr(scraper, "stored_amazon_urls", lambda *_: (urls, len(urls)))
    monkeypatch.setattr(scraper, "fetch_page_selenium", lambda url: "<span id='productTitle'>HP Test 8GB RAM 512GB SSD 15.6 inch</span>")
    captured = []
    monkeypatch.setattr(scraper, "upsert_products", lambda products, *_: (captured.extend(products) or (1, 0)))
    summary = scraper.scrape_stored_products()
    assert summary["successful_urls"] == 1 and summary["failed_urls"] == 1
    assert summary["products_found"] == 1 and captured[0]["product_url"] == urls[0]


def test_upsert_updates_asin_without_duplicates(monkeypatch):
    saved = []
    monkeypatch.setattr(scraper, "_read_rows", lambda *_: [{"asin": "B012345678", "product_url": "https://www.amazon.in/dp/B012345678", "title": "Old"}])
    monkeypatch.setattr(scraper, "save_rows", lambda rows, *_: saved.extend(rows))
    inserted, updated = scraper.upsert_products([{ "asin": "B012345678", "product_url": "https://www.amazon.in/dp/B012345678", "title": "New" }])
    assert (inserted, updated) == (0, 1) and len(saved) == 1 and saved[0]["title"] == "New"


def test_prediction_classification_and_no_urls_api():
    train_models()
    payload = {"ram_gb": 16, "storage_gb": 512, "processor_score": 7, "gpu_score": 7, "screen_size": 15.6, "rating": 4.3, "brand": "ASUS"}
    client = app.test_client()
    assert client.post("/api/predict-price", json=payload).status_code == 200
    assert client.post("/api/classify", json=payload).status_code == 200
    response = client.post("/api/scrape")
    assert response.status_code == 200 and response.json["message"] == "No Amazon URLs are available for scraping."


def test_recommendations():
    data = pd.DataFrame([{"title":"One","brand":"HP","price":50000,"rating":4.2,"ram_gb":16,"storage_gb":512,"processor_score":5,"gpu_score":0,"screen_size":15.6}])
    assert recommend_laptops(data, {"ram_gb":16,"storage_gb":512,"budget":60000})[0]["title"] == "One"
