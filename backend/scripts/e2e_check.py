"""Quick end-to-end API acceptance checks against a running Flask server."""
import json
import urllib.error
import urllib.request


def call(method, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json"} if body is not None else {}
    req = urllib.request.Request(
        "http://127.0.0.1:5000" + path, data=data, method=method, headers=headers
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


def main():
    checks = []
    status, payload = call("GET", "/api/datasets/kaggle")
    checks.append(("kaggle records", payload.get("records", 0) >= 1000, payload.get("records")))

    status, payload = call("GET", "/api/catalog?source=kaggle&per_page=3")
    checks.append(("catalog", status == 200 and len(payload.get("records", [])) == 3, payload.get("total")))

    predict_body = {
        "source": "kaggle",
        "brand": "ASUS",
        "ram_gb": 16,
        "storage_gb": 512,
        "processor": "Intel Core i7",
        "gpu": "NVIDIA RTX 4050",
        "screen_size": 15.6,
        "rating": 4.2,
        "budget": 100000,
    }
    status, payload = call("POST", "/api/predict-price", predict_body)
    checks.append((
        "predict",
        status == 200
        and payload["linear_regression"]["predicted_price"] > 0
        and payload["random_forest"]["predicted_price"] > 0,
        payload.get("best_model"),
    ))

    status, payload = call("POST", "/api/classify", predict_body)
    checks.append((
        "classify",
        status == 200 and payload.get("category") in {"Budget", "Mid Range", "Premium"},
        payload.get("category"),
    ))

    status, payload = call("POST", "/api/recommend", predict_body)
    checks.append((
        "recommend",
        status == 200 and len(payload.get("recommendations", [])) >= 1,
        len(payload.get("recommendations", [])),
    ))

    status, payload = call("GET", "/api/ml-analysis?source=kaggle")
    checks.append((
        "ml",
        status == 200 and "linear_regression" in payload and "classification" in payload,
        payload.get("best_model"),
    ))

    status, payload = call("GET", "/api/catalog?source=amazon")
    checks.append((
        "amazon catalog responds",
        status == 200 and "source" in payload,
        "total=%s" % payload.get("total"),
    ))

    status, payload = call("POST", "/api/scrape", {"query": "https://www.not-a-supported-shop.example/"})
    checks.append(("unsupported scrape", status == 200 and payload.get("success") is False, payload.get("message", "")[:80]))

    print("Trying Amazon scrape (may be blocked by anti-bot)...")
    status, payload = call("POST", "/api/scrape", {"query": "Amazon laptops"})
    checks.append((
        "amazon scrape attempted",
        status == 200,
        "success=%s msg=%s" % (payload.get("success"), str(payload.get("message"))[:120]),
    ))
    if payload.get("success"):
        source = payload.get("source_key")
        status, catalog = call("GET", "/api/catalog?source=%s&per_page=3" % source)
        checks.append(("scraped catalog", catalog.get("total", 0) > 0, catalog.get("total")))
        predict_body["source"] = source
        status, prediction = call("POST", "/api/predict-price", predict_body)
        checks.append((
            "scraped predict",
            status == 200 and prediction.get("random_forest", {}).get("predicted_price", 0) > 0,
            prediction.get("best_model"),
        ))
        status, classify = call("POST", "/api/classify", predict_body)
        checks.append((
            "scraped classify",
            status == 200 and classify.get("category") in {"Budget", "Mid Range", "Premium"},
            classify.get("category"),
        ))
        status, recommend = call("POST", "/api/recommend", predict_body)
        checks.append((
            "scraped recommend",
            status == 200 and len(recommend.get("recommendations", [])) >= 1,
            len(recommend.get("recommendations", [])),
        ))
        status, analysis = call("GET", "/api/ml-analysis?source=%s" % source)
        checks.append((
            "scraped ml",
            status == 200 and "linear_regression" in analysis,
            analysis.get("best_model"),
        ))

    # Source switching: Kaggle still intact after Amazon scrape
    status, kaggle_catalog = call("GET", "/api/catalog?source=kaggle&per_page=1")
    checks.append((
        "kaggle intact after scrape",
        status == 200 and kaggle_catalog.get("total", 0) >= 1000,
        kaggle_catalog.get("total"),
    ))

    print("Trying Flipkart scrape (Coming Soon)...")
    status, payload = call("POST", "/api/scrape", {"query": "Flipkart laptops"})
    checks.append((
        "flipkart coming soon",
        status == 200 and payload.get("success") is False and "coming soon" in str(payload.get("message", "")).casefold(),
        str(payload.get("message"))[:100],
    ))

    print("---")
    for name, ok, detail in checks:
        print(("PASS" if ok else "FAIL"), name, "->", detail)
    print("ALL_OK" if all(item[1] for item in checks) else "SOME_FAILED")


if __name__ == "__main__":
    main()
