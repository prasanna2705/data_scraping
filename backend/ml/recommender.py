"""KNN-based similar laptop recommendations from the active dataset."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ml.models import RECOMMENDATION_FEATURES
from ml.train import load_model, prepare_training_frame
from utils.feature_extraction import normalize_payload


def recommend_laptops(data: pd.DataFrame, requirements: dict, limit: int = 5, source: str = "kaggle") -> list[dict]:
    """Return real laptops from the active source nearest to the request."""
    if data is None or data.empty:
        return []

    values = normalize_payload(requirements)
    frame = data.copy()
    for column in RECOMMENDATION_FEATURES:
        frame[column] = pd.to_numeric(frame.get(column), errors="coerce")

    candidates = frame[frame["price"].notna() & (frame["price"] > 0)].copy()
    if requirements.get("budget") not in (None, ""):
        candidates = candidates[candidates["price"] <= float(requirements["budget"])]
    if requirements.get("brand"):
        brand = str(requirements["brand"]).casefold()
        if brand and brand != "any":
            candidates = candidates[candidates["brand"].astype(str).str.casefold() == brand]
    if requirements.get("ram_gb"):
        try:
            min_ram = float(requirements["ram_gb"])
            preferred = candidates[candidates["ram_gb"].fillna(0) >= min_ram]
            if not preferred.empty:
                candidates = preferred
        except (TypeError, ValueError):
            pass
    if candidates.empty:
        return []

    try:
        knn = load_model(source, "knn_recommender.pkl")
        training = prepare_training_frame(source)
    except ValueError:
        return _fallback_similarity(candidates, values, limit)

    # Align candidates to training index where possible via title
    desired = {
        "ram_gb": float(values.get("ram_gb") or candidates["ram_gb"].median()),
        "storage_gb": float(values.get("storage_gb") or candidates["storage_gb"].median()),
        "processor_score": float(values.get("processor_score") or 5),
        "gpu_score": float(values.get("gpu_score") or 1),
        "screen_size": float(values.get("screen_size") or candidates["screen_size"].median() or 15.6),
        "rating": float(values.get("rating") or candidates["rating"].median() or 3.5),
        "price": float(requirements.get("budget") or candidates["price"].median()),
    }

    scaler = knn["scaler"]
    model = knn["model"]
    vector = scaler.transform(pd.DataFrame([desired])[RECOMMENDATION_FEATURES])
    n = min(max(limit * 3, limit), len(training))
    model.set_params(n_neighbors=n)
    distances, indices = model.kneighbors(vector)
    results = []
    seen = set()
    for distance, idx in zip(distances[0], indices[0]):
        row = training.iloc[int(idx)]
        title = str(row.get("title"))
        if title in seen:
            continue
        # Must exist in filtered candidates when budget/brand applied
        match = candidates[candidates["title"].astype(str) == title]
        if match.empty:
            continue
        record = match.iloc[0].to_dict()
        record["similarity"] = round(float(1 / (1 + distance)), 4)
        record["distance"] = round(float(distance), 4)
        results.append(record)
        seen.add(title)
        if len(results) >= limit:
            break
    if results:
        return results
    return _fallback_similarity(candidates, values, limit)


def _fallback_similarity(candidates: pd.DataFrame, values: dict, limit: int) -> list[dict]:
    work = candidates.copy()
    for column in RECOMMENDATION_FEATURES:
        work[column] = pd.to_numeric(work[column], errors="coerce").fillna(work[column].median() if work[column].notna().any() else 0)
    desired = np.array([
        float(values.get("ram_gb") or work["ram_gb"].median()),
        float(values.get("storage_gb") or work["storage_gb"].median()),
        float(values.get("processor_score") or 5),
        float(values.get("gpu_score") or 1),
        float(values.get("screen_size") or 15.6),
        float(values.get("rating") or 3.5),
        float(values.get("budget") or work["price"].median()),
    ], dtype=float)
    matrix = work[RECOMMENDATION_FEATURES].to_numpy(dtype=float)
    # simple scaled Euclidean
    scale = matrix.std(axis=0)
    scale[scale == 0] = 1
    distances = np.linalg.norm((matrix - desired) / scale, axis=1)
    work = work.assign(distance=distances, similarity=1 / (1 + distances))
    return work.sort_values(["similarity", "rating"], ascending=False).head(limit).to_dict("records")
