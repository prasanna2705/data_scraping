"""Feature extraction helpers for raw laptop listing titles.

Processor and GPU scores are simple engineered tiers, not benchmark scores.
"""
import re


def clean_price(value):
    """Return an Indian-price number, or 0 when no usable price is present."""
    if value is None:
        return 0
    digits = re.sub(r"[^\d]", "", str(value))
    return int(digits) if digits else 0


def clean_rating(value):
    """Return a rating from 0 to 5, or 0 when unavailable/invalid."""
    match = re.search(r"(\d+(?:\.\d+)?)", str(value or ""))
    rating = float(match.group(1)) if match else 0.0
    return rating if 0 <= rating <= 5 else 0.0


def extract_brand(title):
    for brand in ("HP", "Dell", "Lenovo", "ASUS", "Acer", "MSI", "Apple", "Samsung", "Microsoft", "LG", "Xiaomi", "Infinix", "Honor", "Chuwi"):
        if re.search(rf"\b{re.escape(brand)}\b", title, re.IGNORECASE):
            return brand
    return "Unknown"


def extract_ram(title):
    """Extract RAM only when it is explicitly labelled as memory."""
    match = re.search(r"\b(\d+)\s*GB\s*(?:RAM|DDR\d?|LPDDR\d?)\b", title, re.I)
    return int(match.group(1)) if match else 0


def extract_storage(title):
    """Extract capacity only when associated with a storage medium."""
    match = re.search(r"\b(\d+(?:\.\d+)?)\s*(TB|GB)\s*(?:SSD|HDD|EMMC|UFS|NVME)\b", title, re.I)
    if not match:
        return 0
    value = float(match.group(1))
    return int(value * 1024) if match.group(2).upper() == "TB" else int(value)


def extract_processor_score(title):
    title = title.lower()
    for tier, score in (("i9", 9), ("ryzen 9", 9), ("i7", 7), ("ryzen 7", 7), ("i5", 5), ("ryzen 5", 5), ("i3", 3), ("ryzen 3", 3)):
        if tier in title:
            return score
    return 7 if any(chip in title for chip in ("m3", "m2", "m1")) else 0


def extract_gpu_score(title):
    title = title.lower()
    for gpu, score in (("rtx 4090", 10), ("rtx 4080", 9), ("rtx 4070", 8), ("rtx 4060", 7), ("rtx 4050", 6), ("rtx 3050", 5), ("gtx 1650", 4), ("intel iris", 2), ("integrated", 1)):
        if gpu in title:
            return score
    return 0


def extract_screen_size(title):
    match = re.search(r"\b(1[0-9](?:\.\d+)?)\s*(?:inch|inches|\")", title, re.I)
    return float(match.group(1)) if match else 0.0


def extract_features(title, price, rating):
    """Convert a raw listing to the shared CSV/API schema."""
    numeric_price, numeric_rating = clean_price(price), clean_rating(rating)
    ram = extract_ram(title)
    return {"title": title.strip(), "price": numeric_price, "rating": numeric_rating, "ram_gb": ram, "storage_gb": extract_storage(title), "processor_score": extract_processor_score(title), "gpu_score": extract_gpu_score(title), "screen_size": extract_screen_size(title), "brand": extract_brand(title), "recommended": int(numeric_price > 0 and numeric_rating >= 4 and ram >= 8)}
