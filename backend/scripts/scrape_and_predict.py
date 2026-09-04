import json
import urllib.request

req = urllib.request.Request(
    "http://127.0.0.1:5000/api/scrape",
    data=json.dumps({"query": "Amazon laptops", "max_products": 48}).encode(),
    method="POST",
    headers={"Content-Type": "application/json"},
)
print(urllib.request.urlopen(req, timeout=120).read().decode())

req2 = urllib.request.Request(
    "http://127.0.0.1:5000/api/predict-price",
    data=json.dumps({
        "source": "amazon",
        "brand": "Lenovo",
        "ram_gb": 16,
        "storage_gb": 512,
        "processor": "Intel Core i7",
        "gpu": "NVIDIA RTX 3050",
        "screen_size": 15.6,
        "rating": 4.2,
    }).encode(),
    method="POST",
    headers={"Content-Type": "application/json"},
)
try:
    print("PREDICT", urllib.request.urlopen(req2, timeout=60).read().decode())
except Exception as exc:  # noqa: BLE001
    print("PREDICT ERR", exc)
    if hasattr(exc, "read"):
        print(exc.read().decode())
