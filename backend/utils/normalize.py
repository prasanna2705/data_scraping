"""Cleaning, normalization, and deduplication for laptop records."""
from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd

from utils.feature_extraction import (
    clean_price,
    clean_rating,
    extract_brand,
    extract_gpu_score,
    extract_processor_score,
    extract_ram,
    extract_screen_size,
    extract_storage,
    extract_storage_type,
)
from utils.schema import SCHEMA_COLUMNS


def parse_ram(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(int(value))
    match = re.search(r"(\d+)\s*GB", str(value), re.I)
    if match:
        return float(match.group(1))
    digits = re.sub(r"[^\d]", "", str(value))
    return float(digits) if digits else None


def parse_storage(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(int(value))
    text = str(value)
    match = re.search(r"(\d+(?:\.\d+)?)\s*(TB|GB)", text, re.I)
    if not match:
        return None
    amount = float(match.group(1))
    return float(int(amount * 1024)) if match.group(2).upper() == "TB" else float(int(amount))


def parse_screen(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    match = re.search(r"(\d+(?:\.\d+)?)", str(value))
    return float(match.group(1)) if match else None


def normalize_record(raw: dict, source_label: str) -> dict:
    """Normalize one product dict into the shared schema. Missing fields stay empty."""
    title = str(raw.get("title") or "").strip()
    brand = str(raw.get("brand") or "").strip() or (extract_brand(title) if title else "Unknown")
    processor = str(raw.get("processor") or raw.get("cpu") or "").strip()
    gpu = str(raw.get("gpu") or "").strip()
    blob = " ".join(part for part in (title, processor, gpu) if part)

    price_raw = raw.get("price")
    price = clean_price(price_raw) if not isinstance(price_raw, (int, float)) else float(price_raw or 0)
    if isinstance(price_raw, (int, float)) and price_raw and price == 0:
        price = float(price_raw)

    rating_raw = raw.get("rating")
    if rating_raw in (None, "", np.nan):
        rating = None
    elif isinstance(rating_raw, (int, float)):
        rating = float(rating_raw) if 0 < float(rating_raw) <= 5 else None
    else:
        rating = clean_rating(rating_raw) or None
        if rating is not None and rating <= 0:
            rating = None

    ram = parse_ram(raw.get("ram_gb", raw.get("ram")))
    if ram is None and title:
        extracted = extract_ram(title)
        ram = float(extracted) if extracted else None
    if ram is not None and ram <= 0:
        ram = None

    storage = parse_storage(raw.get("storage_gb", raw.get("storage")))
    if storage is None and title:
        extracted = extract_storage(title)
        storage = float(extracted) if extracted else None
    if storage is not None and storage <= 0:
        storage = None

    screen = parse_screen(raw.get("screen_size"))
    if screen is None and title:
        extracted = extract_screen_size(title)
        screen = float(extracted) if extracted else None
    if screen is not None and screen <= 0:
        screen = None

    processor_score = raw.get("processor_score")
    if processor_score in (None, ""):
        processor_score = extract_processor_score(processor or blob)
    gpu_score = raw.get("gpu_score")
    if gpu_score in (None, ""):
        gpu_score = extract_gpu_score(gpu or blob)

    storage_type = str(raw.get("storage_type") or "").strip()
    if not storage_type and title:
        storage_type = extract_storage_type(title)

    return {
        "title": title,
        "price": price if price else None,
        "rating": rating,
        "brand": brand,
        "ram_gb": ram,
        "storage_gb": storage,
        "storage_type": storage_type or None,
        "processor": processor or None,
        "processor_score": int(processor_score) if processor_score not in (None, "") else None,
        "gpu": gpu or None,
        "gpu_score": int(gpu_score) if gpu_score not in (None, "") else None,
        "screen_size": screen,
        "product_url": str(raw.get("product_url") or "").strip() or None,
        "image_url": str(raw.get("image_url") or "").strip() or None,
        "availability": str(raw.get("availability") or "").strip() or None,
        "source": source_label,
        "asin": str(raw.get("asin") or "").strip() or None,
        "source_url": str(raw.get("source_url") or "").strip() or None,
        "scraped_at": str(raw.get("scraped_at") or "").strip() or None,
    }


def is_valid_laptop(record: dict) -> bool:
    title = str(record.get("title") or "").strip()
    if len(title) < 3:
        return False
    price = record.get("price")
    if price is None:
        return False
    try:
        return float(price) > 0
    except (TypeError, ValueError):
        return False


def dedupe_records(records: list[dict]) -> tuple[list[dict], int]:
    """Remove duplicates by ASIN, URL, or normalized title+brand."""
    seen: set[str] = set()
    unique: list[dict] = []
    duplicates = 0
    for record in records:
        keys = []
        asin = str(record.get("asin") or "").strip().upper()
        url = str(record.get("product_url") or "").strip().rstrip("/").casefold()
        title = re.sub(r"\s+", " ", str(record.get("title") or "").casefold()).strip()
        brand = str(record.get("brand") or "").casefold().strip()
        if asin:
            keys.append(f"asin:{asin}")
        if url:
            keys.append(f"url:{url}")
        if title:
            keys.append(f"title:{brand}|{title}")
        if keys and any(key in seen for key in keys):
            duplicates += 1
            continue
        for key in keys:
            seen.add(key)
        unique.append(record)
    return unique, duplicates


def clean_dataframe(frame: pd.DataFrame, source_label: str) -> tuple[pd.DataFrame, dict]:
    """Normalize, validate, and deduplicate a raw dataframe."""
    discovered = len(frame)
    normalized = [normalize_record(row, source_label) for row in frame.to_dict("records")]
    valid = [row for row in normalized if is_valid_laptop(row)]
    invalid = len(normalized) - len(valid)
    unique, duplicates = dedupe_records(valid)
    cleaned = pd.DataFrame(unique)
    for column in SCHEMA_COLUMNS:
        if column not in cleaned.columns:
            cleaned[column] = None
    cleaned = cleaned[SCHEMA_COLUMNS] if not cleaned.empty else pd.DataFrame(columns=SCHEMA_COLUMNS)
    stats = {
        "products_discovered": discovered,
        "valid_products": len(unique),
        "duplicates_removed": duplicates,
        "invalid_records": invalid,
        "failed_records": 0,
    }
    return cleaned, stats
