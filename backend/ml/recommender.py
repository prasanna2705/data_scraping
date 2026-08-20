"""Content-based recommendations using scaled features and cosine similarity."""
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler

RECOMMENDATION_FEATURES = ["ram_gb", "storage_gb", "processor_score", "gpu_score", "screen_size", "rating", "price"]


def recommend_laptops(data, requirements, limit=5):
    if data.empty:
        return []
    frame = data.copy()
    for column in RECOMMENDATION_FEATURES:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0)
    candidates = frame[frame["price"] > 0]
    if requirements.get("budget"):
        candidates = candidates[candidates["price"] <= float(requirements["budget"])]
    if requirements.get("min_rating"):
        candidates = candidates[candidates["rating"] >= float(requirements["min_rating"])]
    if requirements.get("brand"):
        candidates = candidates[candidates["brand"].str.casefold() == str(requirements["brand"]).casefold()]
    if candidates.empty:
        return []
    desired = {column: float(requirements.get(column, candidates[column].median())) for column in RECOMMENDATION_FEATURES}
    scaler = StandardScaler()
    matrix = scaler.fit_transform(candidates[RECOMMENDATION_FEATURES])
    desired_vector = scaler.transform(pd.DataFrame([desired])[RECOMMENDATION_FEATURES])
    candidates = candidates.assign(similarity=cosine_similarity(matrix, desired_vector).ravel())
    return candidates.sort_values(["similarity", "rating"], ascending=False).head(limit).to_dict("records")
