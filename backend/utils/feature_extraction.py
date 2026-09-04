"""Feature extraction helpers for raw laptop listing titles and user payloads.

Processor and GPU scores are simple engineered tiers, not benchmark scores.
"""
from __future__ import annotations

import re


def clean_price(value):
    """Return an Indian-price number, or 0 when no usable price is present."""
    if value is None:
        return 0
    text = str(value)
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else 0


def clean_rating(value):
    """Return a rating from 0 to 5, or 0 when unavailable/invalid."""
    match = re.search(r"(\d+(?:\.\d+)?)", str(value or ""))
    rating = float(match.group(1)) if match else 0.0
    return rating if 0 <= rating <= 5 else 0.0


def extract_brand(title):
    brands = (
        "HP", "Dell", "Lenovo", "ASUS", "Acer", "MSI", "Apple", "Samsung",
        "Microsoft", "LG", "Xiaomi", "Infinix", "Honor", "Chuwi", "OnePlus",
        "Realme", "Avita", "Fujitsu", "Toshiba", "Sony", "Razer", "Alienware",
    )
    for brand in brands:
        if re.search(rf"\b{re.escape(brand)}\b", str(title), re.IGNORECASE):
            return brand
    return "Unknown"


def extract_ram(title):
    """Extract RAM only when it is explicitly labelled as memory."""
    match = re.search(r"\b(\d+)\s*GB\s*(?:RAM|DDR\d?|LPDDR\d?)\b", str(title), re.I)
    if match:
        return int(match.group(1))
    match = re.search(r"\b(\d+)\s*GB\b", str(title), re.I)
    return int(match.group(1)) if match else 0


def extract_storage(title):
    """Extract capacity only when associated with a storage medium."""
    text = str(title)
    match = re.search(r"\b(\d+(?:\.\d+)?)\s*(TB|GB)\s*(?:SSD|HDD|EMMC|UFS|NVME|Flash)\b", text, re.I)
    if not match:
        # Fall back only when RAM is already labelled separately.
        match = re.search(r"\b(\d+(?:\.\d+)?)\s*(TB|GB)\b(?!\s*RAM)", text, re.I)
        if not match:
            return 0
        # Prefer the largest non-RAM-looking capacity if multiple exist.
        candidates = re.findall(r"\b(\d+(?:\.\d+)?)\s*(TB|GB)\b(?!\s*RAM)", text, re.I)
        if candidates:
            amounts = [
                float(val) * 1024 if unit.upper() == "TB" else float(val)
                for val, unit in candidates
            ]
            return int(max(amounts))
    value = float(match.group(1))
    return int(value * 1024) if match.group(2).upper() == "TB" else int(value)


def extract_storage_type(title):
    match = re.search(r"\b(SSD|HDD|EMMC|UFS|NVME|Flash)\b", str(title), re.I)
    return match.group(1).upper() if match else "Unknown"


def extract_processor_score(title):
    text = str(title).lower()
    for tier, score in (
        ("i9", 9), ("ryzen 9", 9), ("i7", 7), ("ryzen 7", 7),
        ("i5", 5), ("ryzen 5", 5), ("i3", 3), ("ryzen 3", 3),
        ("pentium", 2), ("celeron", 1),
    ):
        if tier in text:
            return score
    return 7 if any(chip in text for chip in ("m3", "m2", "m1")) else 0


def extract_gpu_score(title):
    text = str(title).lower()
    for gpu, score in (
        ("rtx 4090", 10), ("rtx 4080", 9), ("rtx 4070", 8), ("rtx 4060", 7),
        ("rtx 4050", 6), ("rtx 3050", 5), ("gtx 1650", 4), ("intel iris", 2),
        ("iris", 2), ("uhd", 1), ("integrated", 1),
    ):
        if gpu in text:
            return score
    return 0


def extract_screen_size(title):
    match = re.search(r"\b(1[0-9](?:\.\d+)?)\s*(?:inch|inches|\")", str(title), re.I)
    return float(match.group(1)) if match else 0.0


def extract_features(title, price, rating):
    """Convert a raw listing to the shared CSV/API schema."""
    numeric_price, numeric_rating = clean_price(price), clean_rating(rating)
    ram = extract_ram(title)
    return {
        "title": str(title).strip(),
        "price": numeric_price,
        "rating": numeric_rating,
        "ram_gb": ram,
        "storage_gb": extract_storage(title),
        "storage_type": extract_storage_type(title),
        "cpu": "",
        "processor": "",
        "gpu": "",
        "processor_score": extract_processor_score(title),
        "gpu_score": extract_gpu_score(title),
        "screen_size": extract_screen_size(title),
        "brand": extract_brand(title),
        "recommended": int(numeric_price > 0 and numeric_rating >= 4 and ram >= 8),
    }


def normalize_payload(payload):
    """Accept friendly CPU/GPU strings while retaining the shared model schema."""
    data = dict(payload or {})
    for field in ("ram_gb", "storage_gb", "screen_size", "rating", "budget"):
        if field not in data or data[field] in (None, ""):
            if field != "budget":
                data[field] = None
            continue
        try:
            data[field] = float(data[field])
        except (TypeError, ValueError):
            data[field] = None
    data["ram_gb"] = int(data["ram_gb"]) if data.get("ram_gb") is not None else None
    data["storage_gb"] = int(data["storage_gb"]) if data.get("storage_gb") is not None else None
    cpu = str(data.get("processor") or data.get("cpu") or "")
    gpu = str(data.get("gpu") or "")
    data["processor_score"] = (
        extract_processor_score(cpu) if cpu else float(data.get("processor_score", 0) or 0)
    )
    data["gpu_score"] = extract_gpu_score(gpu) if gpu else float(data.get("gpu_score", 0) or 0)
    data["brand"] = str(data.get("brand") or "Unknown").strip() or "Unknown"
    data["processor"] = cpu
    data["gpu"] = gpu
    return data
