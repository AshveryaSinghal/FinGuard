import json, hashlib
from datetime import datetime, timezone
import joblib, numpy as np, pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.metrics import precision_recall_curve, precision_score, recall_score, f1_score, roc_auc_score, average_precision_score
from sklearn.ensemble import IsolationForest
from xgboost import XGBClassifier
from app.config import settings
from app.ml import FEATURES

txp=settings.raw_data_dir/"train_transaction.csv"; idp=settings.raw_data_dir/"train_identity.csv"
if not txp.exists() or not idp.exists(): raise SystemExit("Missing IEEE-CIS CSVs in data/raw/")
tx=pd.read_csv(txp); ident=pd.read_csv(idp,usecols=["TransactionID","DeviceType","DeviceInfo"])
df=tx.merge(ident,on="TransactionID",how="left").sort_values("TransactionDT")
df["Transaction_hour"]=(df.TransactionDT//3600)%24; df["Transaction_day"]=df.TransactionDT//86400
X=df[FEATURES]; y=df["isFraud"].astype(int)
n=len(df); a=int(n*.70); b=int(n*.85)
Xtr,Xv,Xte=X.iloc[:a],X.iloc[a:b],X.iloc[b:]; ytr,yv,yte=y.iloc[:a],y.iloc[a:b],y.iloc[b:]
cat=[c for c in FEATURES if X[c].dtype=="object"]; num=[c for c in FEATURES if c not in cat]
pre=ColumnTransformer([("num",Pipeline([("imp",SimpleImputer(strategy="median")),("scale",StandardScaler())]),num),
 ("cat",Pipeline([("imp",SimpleImputer(strategy="most_frequent")),("oh",OneHotEncoder(handle_unknown="ignore",min_frequency=20))]),cat)])
ratio=max(1,float((ytr==0).sum()/max(1,(ytr==1).sum())))
model=XGBClassifier(n_estimators=500,max_depth=6,learning_rate=.05,subsample=.8,colsample_bytree=.8,
 eval_metric="aucpr",tree_method="hist",scale_pos_weight=ratio,random_state=settings.random_seed,n_jobs=-1)
sup=Pipeline([("pre",pre),("model",model)]); sup.fit(Xtr,ytr)
pv=sup.predict_proba(Xv)[:,1]
precision,recall,thresholds=precision_recall_curve(yv,pv)
valid=np.where((precision[:-1]>=settings.target_precision)&(recall[:-1]>=settings.min_recall))[0]
if len(valid): threshold=float(thresholds[valid[np.argmax(recall[:-1][valid])]])
else:
    f=2*precision[:-1]*recall[:-1]/(precision[:-1]+recall[:-1]+1e-12)
    threshold=float(thresholds[int(np.argmax(f))])
pt=sup.predict_proba(Xte)[:,1]; pred=(pt>=threshold).astype(int)
metrics={"precision":precision_score(yte,pred,zero_division=0),"recall":recall_score(yte,pred,zero_division=0),
 "f1":f1_score(yte,pred,zero_division=0),"roc_auc":roc_auc_score(yte,pt),"pr_auc":average_precision_score(yte,pt),
 "test_rows":len(yte),"test_fraud_rows":int(yte.sum())}
ano=Pipeline([("pre",pre),("model",IsolationForest(n_estimators=300,contamination="auto",
 random_state=settings.random_seed,n_jobs=-1))]); normal=Xtr[ytr==0]; ano.fit(normal)
raw=-ano.decision_function(Xv); p01,p99=np.quantile(raw,[.01,.99])
version=datetime.now(timezone.utc).strftime("ieee-%Y%m%dT%H%M%SZ")
joblib.dump(sup,settings.model_dir/"supervised_pipeline.joblib")
joblib.dump(ano,settings.model_dir/"anomaly_pipeline.joblib")
meta={"version":version,"dataset":"IEEE-CIS Fraud Detection","decision_threshold":threshold,
 "metrics":metrics,"anomaly_calibration":{"p01":float(p01),"p99":float(p99)},
 "split":"chronological 70/15/15","features":FEATURES}
(settings.model_dir/"metadata.json").write_text(json.dumps(meta,indent=2))
print(json.dumps(meta,indent=2))
print("Training complete. Metrics above are from this run; no metrics are hardcoded.")
