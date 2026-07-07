"""Exact V3 inference from the precomputed, reproducible feature store."""
import json
from functools import lru_cache
import duckdb
import joblib
import numpy as np
import pandas as pd
from app.config import settings

@lru_cache(maxsize=1)
def load_bundle():
    required = ["supervised_bundle.joblib", "anomaly_bundle.joblib", "metadata.json"]
    missing = [name for name in required if not (settings.model_dir / name).exists()]
    if missing:
        raise RuntimeError(f"Missing V3 artifacts: {', '.join(missing)}")
    sup = joblib.load(settings.model_dir / "supervised_bundle.joblib")
    ano = joblib.load(settings.model_dir / "anomaly_bundle.joblib")
    meta = json.loads((settings.model_dir / "metadata.json").read_text(encoding="utf-8"))
    if str(meta.get("model_generation", "")).upper() != "V3":
        raise RuntimeError("metadata.json is not a FinGuard V3 artifact")
    return sup, ano, meta


def readiness():
    sup, _, meta = load_bundle()
    if not settings.feature_store_path.exists():
        raise RuntimeError("V3 feature store missing. Run: python -m scripts.build_feature_store")
    return {"version": meta["version"], "features": len(sup["model_features"]), "feature_store": True}


def _feature_row(transaction_id: int, columns: list[str]) -> pd.DataFrame:
    select_cols = ", ".join([f'"{c}"' for c in columns])
    path = str(settings.feature_store_path.resolve()).replace("'", "''")
    query = f"SELECT {select_cols} FROM read_parquet('{path}') WHERE TransactionID = ? LIMIT 1"
    frame = duckdb.execute(query, [transaction_id]).fetchdf()
    if frame.empty:
        raise KeyError(f"Transaction {transaction_id} is not present in the V3 feature store")
    return frame[columns].astype("float32")


def predict(transaction_id: int):
    sup, ano, meta = load_bundle()
    x = _feature_row(transaction_id, sup["model_features"])
    probability = float(sup["model"].predict_proba(x)[:, 1][0])
    anomaly_x = x[ano["features"]]
    raw_anomaly = float(-ano["model"].decision_function(anomaly_x)[0])
    lo = float(meta["anomaly_calibration"]["p01"])
    hi = float(meta["anomaly_calibration"]["p99"])
    anomaly = float(np.clip((raw_anomaly - lo) / (hi - lo + 1e-12), 0, 1))
    return probability, anomaly, meta


TIER_AUTOMATIC_CASE = "Automatic case"
TIER_REVIEW = "Review"
TIER_MONITOR = "Monitor"
TIER_LOW = "Low"


def tier_for_probability(probability: float, meta: dict):
    p = meta["product_thresholds"]
    critical = float(p["automatic_case"]["threshold"])
    review = float(p["review"]["threshold"])
    monitor = float(p["monitor"]["threshold"])
    if probability >= critical:
        return TIER_AUTOMATIC_CASE, "Automatic case creation", critical
    if probability >= review:
        return TIER_REVIEW, "Analyst review", review
    if probability >= monitor:
        return TIER_MONITOR, "Enhanced monitoring", monitor
    return TIER_LOW, "No model escalation", monitor
