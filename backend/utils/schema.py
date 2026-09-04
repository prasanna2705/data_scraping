"""Canonical laptop record schema shared by Kaggle and scraped sources."""

SCHEMA_COLUMNS = [
    "title",
    "price",
    "rating",
    "brand",
    "ram_gb",
    "storage_gb",
    "storage_type",
    "processor",
    "processor_score",
    "gpu",
    "gpu_score",
    "screen_size",
    "product_url",
    "image_url",
    "availability",
    "source",
    "asin",
    "source_url",
    "scraped_at",
]

# Internal source keys used by APIs / frontend state
SOURCE_KEYS = ("kaggle", "amazon", "flipkart", "oneplus", "custom")

# Sources enabled in the current product version
ACTIVE_SOURCE_KEYS = ("kaggle", "amazon")

COMING_SOON_SOURCES = ("flipkart", "oneplus", "custom")

SOURCE_LABELS = {
    "kaggle": "Kaggle",
    "amazon": "Amazon",
    "flipkart": "Flipkart",
    "oneplus": "OnePlus",
    "custom": "Custom",
}
