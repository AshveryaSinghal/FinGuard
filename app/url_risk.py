"""Experimental lexical URL model adapter.

The installed V2 model failed broad legitimate bare-apex stress tests. FinGuard therefore
exposes its raw score for research diagnostics but never converts that score into an
automatic allow/block action. A future artifact must pass independent acceptance gates.
"""
import math, re
from functools import lru_cache
from urllib.parse import urlparse, unquote
import joblib
import numpy as np
import pandas as pd
from app.config import settings

SUSPICIOUS_TERMS={"login","signin","verify","verification","secure","security","account","update","bank","banking","wallet","payment","pay","confirm","confirmation","password","credential","bonus","free","gift","prize","reward","invoice","recover","unlock","suspend","urgent"}
FINANCIAL_TERMS={"bank","banking","payment","wallet","card","credit","debit","upi","paypal","invoice","finance","account"}
SHORTENER_DOMAINS=("bit.ly","tinyurl.com","t.co","goo.gl","ow.ly","is.gd","buff.ly","cutt.ly","rb.gy")
SUSPICIOUS_TLDS=(".zip",".mov",".click",".top",".xyz",".work",".support",".country",".gq",".tk")
FEATURE_NAMES=["url_length","host_length","path_length","query_length","fragment_length","digit_count","digit_ratio","letter_count","letter_ratio","special_count","special_ratio","dot_count","hyphen_count","underscore_count","slash_count","question_count","equals_count","ampersand_count","at_count","percent_count","colon_count","semicolon_count","plus_count","tilde_count","subdomain_count","https_scheme","http_token_count","https_token_in_host","ip_host","punycode","port_present","double_slash_in_path","encoded_char_count","suspicious_term_count","financial_term_count","shortener_domain","suspicious_tld","host_digit_count","host_digit_ratio","host_hyphen_count","path_depth","query_parameter_count","longest_token_length","average_token_length","token_count","url_entropy","host_entropy","repeated_char_runs","brand_like_subdomain_depth"]

def _entropy(text):
    if not text:return 0.0
    ps=[text.count(c)/len(text) for c in set(text)]
    return float(-sum(p*math.log2(p) for p in ps if p>0))
def _ratio(a,b): return float(a/max(b,1))

def extract_features(url:str):
    raw=str(url).strip()
    if not raw or len(raw)>4096: raise ValueError("URL must contain 1 to 4096 characters")
    normalized=raw if "://" in raw else "http://"+raw
    p=urlparse(normalized); host=(p.hostname or "").lower(); path=p.path or ""; query=p.query or ""; fragment=p.fragment or ""
    decoded=unquote(raw); lower=decoded.lower(); letters=sum(c.isalpha() for c in raw); digits=sum(c.isdigit() for c in raw); special=sum(not c.isalnum() for c in raw); host_digits=sum(c.isdigit() for c in host)
    tokens=[t for t in re.split(r"[^a-zA-Z0-9]+",lower) if t]; token_set=set(tokens); lengths=[len(t) for t in tokens]; parts=[x for x in host.split(".") if x]; subdomains=max(0,len(parts)-2)
    vals=[len(raw),len(host),len(path),len(query),len(fragment),digits,_ratio(digits,len(raw)),letters,_ratio(letters,len(raw)),special,_ratio(special,len(raw)),raw.count("."),raw.count("-"),raw.count("_"),raw.count("/"),raw.count("?"),raw.count("="),raw.count("&"),raw.count("@"),raw.count("%"),raw.count(":"),raw.count(";"),raw.count("+"),raw.count("~"),subdomains,int(p.scheme.lower()=="https"),lower.count("http"),int("https" in host),int(bool(re.fullmatch(r"(?:\d{1,3}\.){3}\d{1,3}",host))),int("xn--" in host),int(bool(re.search(r":\d+(?:/|$)",normalized.split("://",1)[-1]))),int("//" in path),raw.count("%"),len(token_set&SUSPICIOUS_TERMS),len(token_set&FINANCIAL_TERMS),int(any(host==d or host.endswith("."+d) for d in SHORTENER_DOMAINS)),int(any(host.endswith(t) for t in SUSPICIOUS_TLDS)),host_digits,_ratio(host_digits,len(host)),host.count("-"),len([x for x in path.split("/") if x]),query.count("&")+1 if query else 0,max(lengths) if lengths else 0,float(np.mean(lengths)) if lengths else 0.0,len(tokens),_entropy(raw),_entropy(host),len(re.findall(r"(.)\1{3,}",raw)),int(subdomains>=3)]
    return dict(zip(FEATURE_NAMES,vals))

@lru_cache(maxsize=1)
def load_url_bundle():
    path=settings.model_dir/"url_bundle.joblib"
    if not path.exists(): return None
    b=joblib.load(path)
    if list(b.get("features",[]))!=FEATURE_NAMES: raise RuntimeError("URL artifact feature contract mismatch")
    return b

def url_readiness():
    b=load_url_bundle()
    return {"ready":bool(b),"accepted":False,"status":"experimental_rejected","message":"V2 failed independent legitimate-domain stress tests; automatic URL verdicts are disabled.","version":b.get("version","unknown") if b else None,"features":len(b["features"]) if b else 49}

def scan_url(url:str):
    b=load_url_bundle(); f=extract_features(url)
    if b is None:return {"ready":False,"accepted":False,"message":"URL model artifact missing","features":f}
    x=pd.DataFrame([f],columns=b["features"]).astype("float32")
    malicious=float(b["model"].predict_proba(x)[0,1])
    evidence=[{"feature":k,"value":f[k]} for k in ("https_scheme","ip_host","punycode","shortener_domain","suspicious_tld","suspicious_term_count","financial_term_count","subdomain_count","url_entropy","url_length")]
    return {"ready":True,"accepted":False,"url":url,"malicious_probability":malicious,"model_verdict":"Experimental score only","verdict":"No automated verdict","recommended_action":"No automatic action — model rejected by acceptance testing","evidence":evidence,"model_version":b.get("version","url-v2"),"evaluation_scope":"Research-only lexical score. This artifact failed independent legitimate-domain stress tests and is not used for allow/block decisions."}
