# Kaggle/Colab-ready URL model trainer. Add the UCI PhiUSIIL CSV as input.
import pandas as pd,numpy as np,joblib,json,math,re,shutil
from pathlib import Path
from urllib.parse import urlparse
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report,average_precision_score,roc_auc_score
from sklearn.ensemble import ExtraTreesClassifier
SUSPICIOUS=('login','verify','secure','account','update','bank','wallet','payment','signin','confirm','bonus','free')
def feat(url):
 u=str(url); p=urlparse(u if '://' in u else 'http://'+u); h=(p.hostname or '').lower(); probs=[u.count(c)/max(len(u),1) for c in set(u)]
 return [len(u),len(h),len((p.path or '')+'?'+(p.query or '')),sum(c.isdigit() for c in u),sum(not c.isalnum() for c in u),u.count('.'),u.count('-'),u.count('/')+u.count('_'),u.count('?')+u.count('=')+u.count('&'),u.count('@'),u.count('%'),max(0,h.count('.')-1),int(p.scheme=='https'),int(bool(re.fullmatch(r'\d{1,3}(\.\d{1,3}){3}',h))),int('xn--' in h),sum(t in u.lower() for t in SUSPICIOUS),-sum(x*math.log2(x) for x in probs if x)]
N=['url_length','host_length','path_length','digit_count','special_count','dot_count','hyphen_count','slash_count','query_count','at_count','percent_count','subdomain_count','https_token','ip_host','punycode','suspicious_terms','entropy']
files=list(Path('/kaggle/input').rglob('*.csv')); assert files,'Add the PhiUSIIL dataset to the notebook'
df=pd.read_csv(files[0]); urlcol=next(c for c in df.columns if c.lower() in ('url','url_')); labelcol=next(c for c in df.columns if c.lower() in ('label','class'))
y=df[labelcol].astype(str); X=pd.DataFrame([feat(x) for x in df[urlcol]],columns=N)
Xtr,Xte,ytr,yte=train_test_split(X,y,test_size=.2,random_state=42,stratify=y)
m=ExtraTreesClassifier(n_estimators=700,min_samples_leaf=2,class_weight='balanced',n_jobs=-1,random_state=42).fit(Xtr,ytr)
p=m.predict(Xte); print(classification_report(yte,p,digits=5))
out=Path('/kaggle/working/finguard_url_artifacts');out.mkdir(exist_ok=True)
joblib.dump({'model':m,'features':N,'version':'phiusiil-url-v1','dataset':'UCI PhiUSIIL','synthetic_data':False},out/'url_bundle.joblib',compress=3)
shutil.make_archive('/kaggle/working/finguard_url_model_artifacts','zip',root_dir=out)
print('/kaggle/working/finguard_url_model_artifacts.zip')
