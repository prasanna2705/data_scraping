"""Orchestrate scraping: resolve → scrape → clean → store (never touches Kaggle)."""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from datasets import load_dataset, save_dataset, source_label
from scraper.base import ComingSoonError, NoLaptopProductsError, ScrapeBlockedError, UnsupportedSourceError
from scraper.resolver import resolve_query
from utils.normalize import clean_dataframe, normalize_record


def validate_source(raw: str) -> dict:
    try:
        resolved = resolve_query(raw)
        return {
            "valid": True,
            "supported": True,
            "coming_soon": False,
            "source": resolved["source_label"],
            "source_key": resolved["source_key"],
            "url": resolved["url"],
            "message": resolved["message"],
        }
    except ValueError as exc:
        return {"valid": False, "supported": False, "coming_soon": False, "message": str(exc)}
    except ComingSoonError as exc:
        return {"valid": True, "supported": False, "coming_soon": True, "message": str(exc)}
    except UnsupportedSourceError as exc:
        return {"valid": True, "supported": False, "coming_soon": False, "message": str(exc)}


def run_scrape(raw_query: str, max_products: int = 48) -> dict:
    """Scrape a supported source and persist into that source's CSV only."""
    try:
        resolved = resolve_query(raw_query)
    except ValueError as exc:
        return _failure(str(exc), records_found=0)
    except ComingSoonError as exc:
        return _failure(str(exc), records_found=0)
    except UnsupportedSourceError as exc:
        return _failure(str(exc), records_found=0)

    scraper = resolved["scraper"]
    source_key = resolved["source_key"]
    label = resolved["source_label"]
    target_url = resolved["url"]

    try:
        raw_products = scraper.scrape(resolved["query"], url=target_url, max_products=max_products)
    except ScrapeBlockedError as exc:
        return _failure(str(exc), source=label, source_key=source_key)
    except NoLaptopProductsError as exc:
        return _failure(str(exc), source=label, source_key=source_key)
    except UnsupportedSourceError as exc:
        return _failure(str(exc), source=label, source_key=source_key)
    except Exception:
        return _failure(
            f"{label} could not be scraped because the website currently prevents automated access. "
            "Try another supported source or URL.",
            source=label,
            source_key=source_key,
        )

    stamp = datetime.now(timezone.utc).isoformat()
    for product in raw_products:
        product.setdefault("source", label)
        product.setdefault("source_url", target_url)
        product["scraped_at"] = stamp

    frame = pd.DataFrame(raw_products)
    cleaned, stats = clean_dataframe(frame, label)
    if cleaned.empty:
        return {
            "success": False,
            "status": "Failed",
            "source": label,
            "source_key": source_key,
            "products_discovered": stats["products_discovered"],
            "valid_products": 0,
            "duplicates_removed": stats["duplicates_removed"],
            "invalid_records": stats["invalid_records"],
            "failed_records": stats["failed_records"],
            "records_found": 0,
            "new_records": 0,
            "duplicates": stats["duplicates_removed"],
            "message": "No valid laptop products were found.",
        }

    existing = load_dataset(source_key)
    if not existing.empty:
        merged = pd.concat([existing, cleaned], ignore_index=True)
        merged_clean, merge_stats = clean_dataframe(merged.fillna(""), label)
        duplicates_extra = merge_stats["duplicates_removed"]
    else:
        merged_clean = cleaned
        duplicates_extra = stats["duplicates_removed"]

    save_dataset(merged_clean, source_key)
    new_count = max(0, len(merged_clean) - (0 if existing.empty else len(existing)))

    return {
        "success": True,
        "status": "Completed",
        "source": label,
        "source_key": source_key,
        "products_discovered": stats["products_discovered"],
        "valid_products": len(cleaned),
        "duplicates_removed": duplicates_extra,
        "invalid_records": stats["invalid_records"],
        "failed_records": stats["failed_records"],
        "records_found": len(cleaned),
        "new_records": new_count if new_count else len(cleaned),
        "duplicates": duplicates_extra,
        "total_in_source": len(merged_clean),
        "message": f"Scraping completed for {label}.",
        "last_collection": stamp,
    }


def collect_url(url: str, _ignored_path=None) -> dict:
    """Backward-compatible wrapper used by older clients."""
    return run_scrape(url)


def _failure(message: str, source: str = "", source_key: str = "", records_found: int = 0) -> dict:
    return {
        "success": False,
        "status": "Failed",
        "source": source,
        "source_key": source_key,
        "products_discovered": 0,
        "valid_products": 0,
        "duplicates_removed": 0,
        "invalid_records": 0,
        "failed_records": 0,
        "records_found": records_found,
        "new_records": 0,
        "duplicates": 0,
        "message": message,
    }
