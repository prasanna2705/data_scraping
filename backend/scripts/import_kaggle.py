"""Import and normalize the Kaggle laptop-price dataset into data/kaggle/laptops.csv."""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
RAW = BASE / "data" / "_kaggle_raw.csv"
OUT_DIR = BASE / "data" / "kaggle"
SCRAPED = BASE / "data" / "scraped"
SCHEMA = [
    "title", "price", "rating", "brand", "ram_gb", "storage_gb", "storage_type",
    "processor", "processor_score", "gpu", "gpu_score", "screen_size",
    "product_url", "image_url", "availability", "source", "asin", "source_url", "scraped_at",
]


def ram_gb(value) -> float:
    match = re.search(r"(\d+)", str(value))
    return int(match.group(1)) if match else np.nan


def storage_gb(value) -> float:
    match = re.search(r"(\d+(?:\.\d+)?)\s*(TB|GB)", str(value), re.I)
    if not match:
        return np.nan
    amount = float(match.group(1))
    return int(amount * 1024) if match.group(2).upper() == "TB" else int(amount)


def storage_type(value) -> str:
    match = re.search(r"(SSD|HDD|Flash Storage|Hybrid)", str(value), re.I)
    if not match:
        return ""
    return match.group(1).upper().replace("FLASH STORAGE", "FLASH")


def cpu_score(text: str) -> int:
    lowered = str(text).lower()
    tiers = (
        ("i9", 9), ("ryzen 9", 9), ("i7", 7), ("ryzen 7", 7), ("i5", 5),
        ("ryzen 5", 5), ("i3", 3), ("ryzen 3", 3), ("pentium", 2), ("celeron", 1),
        ("atom", 1), ("a9", 2), ("e-series", 1),
    )
    for key, score in tiers:
        if key in lowered:
            return score
    if any(token in lowered for token in ("m3", "m2", "m1")):
        return 7
    return 4


def gpu_score(text: str) -> int:
    lowered = str(text).lower()
    tiers = (
        ("rtx 4090", 10), ("rtx 4080", 9), ("rtx 4070", 8), ("rtx 4060", 7),
        ("gtx 1080", 7), ("gtx 1070", 6), ("gtx 1050", 4), ("gtx 980", 5),
        ("quadro", 6), ("radeon pro", 5), ("radeon r7", 3), ("iris", 3),
        ("uhd", 2), ("hd graphics", 2), ("intel", 1), ("amd", 2),
    )
    for key, score in tiers:
        if key in lowered:
            return score
    return 1


def import_kaggle(raw_path: Path = RAW) -> Path:
    if not raw_path.exists():
        raise FileNotFoundError(
            f"Raw Kaggle CSV missing at {raw_path}. "
            "Download laptop_data.csv from the Kaggle Laptop Price Prediction dataset."
        )
    frame = pd.read_csv(raw_path)
    rows = []
    for idx, row in frame.iterrows():
        company = str(row["Company"]).strip()
        typename = str(row["TypeName"]).strip()
        cpu = str(row["Cpu"]).strip()
        gpu = str(row["Gpu"]).strip()
        inches = row["Inches"]
        screen = f"{inches}\"" if pd.notna(inches) else ""
        # Keep each Kaggle row identifiable — include screen + GPU so near-duplicates stay distinct.
        title = f"{company} {typename} {screen} {cpu} {row['Ram']} {row['Memory']} ({gpu})".strip()
        title = re.sub(r"\s+", " ", title)
        rows.append({
            "title": title,
            "price": round(float(row["Price"]), 2),
            "rating": np.nan,
            "brand": company,
            "ram_gb": ram_gb(row["Ram"]),
            "storage_gb": storage_gb(row["Memory"]),
            "storage_type": storage_type(row["Memory"]),
            "processor": cpu,
            "processor_score": cpu_score(cpu),
            "gpu": gpu,
            "gpu_score": gpu_score(gpu),
            "screen_size": float(inches) if pd.notna(inches) else np.nan,
            "product_url": "",
            "image_url": "",
            "availability": "",
            "source": "Kaggle",
            "asin": str(idx),
            "source_url": "https://www.kaggle.com/datasets/eslamelsolya/laptop-price-prediction",
            "scraped_at": "",
        })
    out = pd.DataFrame(rows)[SCHEMA].drop_duplicates(subset=["title", "brand", "price"], keep="first")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    destination = OUT_DIR / "laptops.csv"
    out.to_csv(destination, index=False)
    for name in ("amazon", "flipkart", "oneplus", "custom"):
        folder = SCRAPED / name
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "laptops.csv"
        if not path.exists():
            pd.DataFrame(columns=SCHEMA).to_csv(path, index=False)
    return destination


if __name__ == "__main__":
    path = import_kaggle()
    print(f"Imported {sum(1 for _ in open(path, encoding='utf-8')) - 1} rows -> {path}")
