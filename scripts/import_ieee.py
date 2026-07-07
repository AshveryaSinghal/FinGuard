import pandas as pd
from app.config import settings
from app.database import Base, engine, SessionLocal
from app.models import Transaction

path=settings.catalog_path
if not path.exists(): raise SystemExit("Run python -m scripts.build_feature_store first.")
df=pd.read_parquet(path)
if settings.max_import_rows>0: df=df.head(settings.max_import_rows)
Base.metadata.create_all(engine); db=SessionLocal()
try:
    db.query(Transaction).delete(); db.commit(); batch=[]
    for r in df.itertuples(index=False):
        def val(x): return None if pd.isna(x) else x
        batch.append(Transaction(transaction_id=int(r.TransactionID),transaction_dt=int(r.TransactionDT),amount=float(r.TransactionAmt),product_cd=val(r.ProductCD),card1=val(r.card1),card4=val(r.card4),card6=val(r.card6),p_emaildomain=val(r.P_emaildomain),device_type=val(r.DeviceType),device_info=val(r.DeviceInfo),is_fraud=bool(r.isFraud),source="IEEE-CIS"))
        if len(batch)>=5000: db.bulk_save_objects(batch); db.commit(); batch=[]
    if batch: db.bulk_save_objects(batch); db.commit()
    print(f"Imported {len(df):,} real IEEE-CIS rows into the operational database.")
finally: db.close()
