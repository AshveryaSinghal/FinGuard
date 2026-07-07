"""Rebuild the exact V3 model matrix from real IEEE-CIS CSVs and the saved V3 bundle.
No labels are fabricated. No synthetic rows are created.
"""
import gc
import joblib
import numpy as np
import pandas as pd
from app.config import settings

sup_path = settings.model_dir / "supervised_bundle.joblib"
if not sup_path.exists():
    raise SystemExit("Missing artifacts/supervised_bundle.joblib")
sup = joblib.load(sup_path)

tx_path = settings.raw_data_dir / "train_transaction.csv"
id_path = settings.raw_data_dir / "train_identity.csv"
if not tx_path.exists() or not id_path.exists():
    raise SystemExit("Place train_transaction.csv and train_identity.csv in data/raw/")

print("Loading real IEEE-CIS files...")
tx = pd.read_csv(tx_path, low_memory=False)
identity = pd.read_csv(id_path, low_memory=False)
df = tx.merge(identity, on="TransactionID", how="left").sort_values(["TransactionDT", "TransactionID"]).reset_index(drop=True)
del tx, identity; gc.collect()

def s(col):
    return df[col].fillna("__MISSING__").astype(str) if col in df else pd.Series("__MISSING__", index=df.index)

df["Transaction_hour"] = ((df.TransactionDT // 3600) % 24).astype("int8")
df["Transaction_day"] = (df.TransactionDT // 86400).astype("int16")
df["Transaction_week"] = (df.TransactionDT // (86400 * 7)).astype("int16")
df["Transaction_dayofweek"] = (df.Transaction_day % 7).astype("int8")
df["TransactionAmt_log"] = np.log1p(df.TransactionAmt).astype("float32")
df["TransactionAmt_decimal"] = (df.TransactionAmt - np.floor(df.TransactionAmt)).astype("float32")
df["card_proxy"] = s("card1")+"_"+s("card2")+"_"+s("card3")+"_"+s("card5")
df["card_address_proxy"] = df.card_proxy+"_"+s("addr1")
df["card_email_proxy"] = df.card_proxy+"_"+s("P_emaildomain")
df["device_proxy"] = s("DeviceType")+"_"+s("DeviceInfo")
df["email_pair"] = s("P_emaildomain")+"_"+s("R_emaildomain")
df["card_device_proxy"] = df.card_proxy+"_"+df.device_proxy
for key in sup.get("history_keys", []):
    if key in df: df[f"{key}__previous_count"] = df.groupby(key, dropna=False).cumcount().astype("float32")
for key in sup.get("time_keys", []):
    prev = df.groupby(key, dropna=False)["TransactionDT"].shift(1)
    delta = df.TransactionDT - prev
    df[f"{key}__seconds_since_previous"] = delta.clip(lower=0).fillna(-1).astype("float32")
    df[f"{key}__rapid_repeat_5m"] = ((delta >= 0) & (delta <= 300)).astype("int8")
    df[f"{key}__rapid_repeat_1h"] = ((delta >= 0) & (delta <= 3600)).astype("int8")
for key in sup.get("amount_keys", []):
    previous_sum = df.groupby(key, dropna=False)["TransactionAmt"].cumsum() - df.TransactionAmt
    previous_count = df.groupby(key, dropna=False).cumcount()
    mean = previous_sum / previous_count.replace(0, np.nan)
    df[f"{key}__previous_amount_mean"] = mean.fillna(-1).astype("float32")
    ratio = df.TransactionAmt / mean.replace(0, np.nan)
    df[f"{key}__amount_vs_history"] = ratio.replace([np.inf,-np.inf], np.nan).fillna(-1).clip(-1,1000).astype("float32")
df["missing_count"] = df.isna().sum(axis=1).astype("int16")
df["missing_ratio"] = df.isna().mean(axis=1).astype("float32")

print("Applying the saved V3 training transformations...")
out = {"TransactionID": df.TransactionID.astype("int64")}
for col in sup["numerical_features"]:
    out[col] = pd.to_numeric(df[col], errors="coerce").fillna(sup["numerical_medians"][col]).astype("float32")
for col in sup["categorical_features"]:
    vals = df[col].fillna("__MISSING__").astype(str)
    out[f"{col}__freq"] = vals.map(sup["frequency_maps"][col]).fillna(0).astype("float32")
model_df = pd.DataFrame(out)
expected = ["TransactionID"] + sup["model_features"]
model_df = model_df[expected]
model_df.to_parquet(settings.feature_store_path, index=False, compression="zstd")

catalog_cols = ["TransactionID","TransactionDT","TransactionAmt","ProductCD","card1","card4","card6","P_emaildomain","DeviceType","DeviceInfo","isFraud"]
df[catalog_cols].to_parquet(settings.catalog_path, index=False, compression="zstd")
print(f"Wrote {len(model_df):,} exact V3 feature rows to {settings.feature_store_path}")
print(f"Wrote transaction catalog to {settings.catalog_path}")
