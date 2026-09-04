"""Load and persist laptop datasets by source without mixing files."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from utils.schema import (
    ACTIVE_SOURCE_KEYS,
    COMING_SOON_SOURCES,
    SCHEMA_COLUMNS,
    SOURCE_KEYS,
    SOURCE_LABELS,
)

BASE = Path(__file__).resolve().parents[1]
DATA_ROOT = BASE / "data"


def source_path(source: str) -> Path:
    key = normalize_source_key(source)
    if key == "kaggle":
        return DATA_ROOT / "kaggle" / "laptops.csv"
    return DATA_ROOT / "scraped" / key / "laptops.csv"


def normalize_source_key(source: str | None) -> str:
    if not source:
        return "kaggle"
    key = str(source).strip().lower()
    aliases = {
        "kaggle": "kaggle",
        "amazon": "amazon",
        "flipkart": "flipkart",
        "oneplus": "oneplus",
        "custom": "custom",
        "web": "amazon",
    }
    if key not in aliases:
        raise ValueError(
            f"Unknown data source '{source}'. "
            f"Supported sources: {', '.join(SOURCE_KEYS)}."
        )
    return aliases[key]


def source_label(source: str) -> str:
    return SOURCE_LABELS.get(normalize_source_key(source), str(source))


def empty_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=SCHEMA_COLUMNS)


def ensure_schema(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.copy()
    for column in SCHEMA_COLUMNS:
        if column not in data.columns:
            data[column] = np.nan
    return data[SCHEMA_COLUMNS]


def load_dataset(source: str = "kaggle") -> pd.DataFrame:
    path = source_path(source)
    if not path.exists():
        return empty_frame()
    data = pd.read_csv(path)
    if data.empty:
        return empty_frame()
    data = ensure_schema(data).replace({np.nan: None})
    return data


def save_dataset(frame: pd.DataFrame, source: str) -> Path:
    path = source_path(source)
    path.parent.mkdir(parents=True, exist_ok=True)
    ensure_schema(frame).to_csv(path, index=False)
    return path


def list_sources() -> list[dict]:
    items = []
    for key in SOURCE_KEYS:
        data = load_dataset(key)
        active = key in ACTIVE_SOURCE_KEYS
        items.append({
            "key": key,
            "label": source_label(key),
            "records": len(data) if active else 0,
            "path": str(source_path(key)),
            "active": active,
            "coming_soon": key in COMING_SOON_SOURCES,
            "status": "available" if active else "Coming Soon",
        })
    return items


def is_active_source(source: str) -> bool:
    return normalize_source_key(source) in ACTIVE_SOURCE_KEYS
