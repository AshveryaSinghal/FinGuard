import json, math
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, desc, func, or_, case
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import Transaction, RiskAssessment, InvestigationCase, CaseNote, Alert
from app.schemas import AnalyseRequest, AlertAction, CaseStatusUpdate, CaseResolutionUpdate, NoteCreate
from app.risk import analyse_transaction
from app.services import dashboard
from app.ml import readiness, load_bundle
from app.url_risk import scan_url, url_readiness
from pydantic import BaseModel

app = FastAPI(title="FinGuard AI ML Core", version="4.0.0", docs_url="/docs")
app.add_middleware(CORSMiddleware, allow_origins=settings.origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


def assessment_payload(ra: RiskAssessment | None):
    if not ra: return None
    return {"score":ra.final_score,"risk_level":ra.risk_level,"fraud_probability":ra.fraud_probability,
            "anomaly_score":ra.anomaly_score,"behavioural_score":ra.behavioural_score,"velocity_score":ra.velocity_score,
            "network_score":ra.network_score,"reasons":json.loads(ra.reasons_json),"model_version":ra.model_version,
            "created_at":ra.created_at.isoformat()}


def transaction_payload(tx: Transaction):
    return {"transaction_id":tx.transaction_id,"transaction_dt":tx.transaction_dt,"amount":tx.amount,"product_cd":tx.product_cd,
            "card_proxy":tx.card1,"card_type":tx.card4,"device_type":tx.device_type,"device_info":tx.device_info,"source":tx.source}

@app.get("/health")
def health():
    try: return {"status":"ready","model":readiness()}
    except Exception as e: return {"status":"degraded","model":{"ready":False,"message":str(e)}}

@app.get("/model")
def model_info():
    _,_,meta=load_bundle(); return meta

@app.get("/dashboard")
def get_dashboard(db:Session=Depends(get_db)): return dashboard(db)

@app.get("/transactions")
def transactions(page:int=1,page_size:int=25,search:str|None=None,status:str|None=None,risk:str|None=None,db:Session=Depends(get_db)):
    page_size=min(max(page_size,1),100)
    q=select(Transaction)
    if search:
        if search.isdigit(): q=q.where(Transaction.transaction_id==int(search))
        else: q=q.where(or_(Transaction.product_cd.ilike(f"%{search}%"),Transaction.device_type.ilike(f"%{search}%")))
    if status == "unassessed": q=q.where(~Transaction.transaction_id.in_(select(RiskAssessment.transaction_id)))
    if status == "assessed": q=q.where(Transaction.transaction_id.in_(select(RiskAssessment.transaction_id)))
    if risk: q=q.where(Transaction.transaction_id.in_(select(RiskAssessment.transaction_id).where(RiskAssessment.risk_level==risk)))
    total=db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows=db.scalars(q.order_by(desc(Transaction.transaction_dt)).offset((page-1)*page_size).limit(page_size)).all()
    ids=[x.transaction_id for x in rows]
    ras={r.transaction_id:r for r in db.scalars(select(RiskAssessment).where(RiskAssessment.transaction_id.in_(ids))).all()} if ids else {}
    return {"items":[{**transaction_payload(x),"risk":ras[x.transaction_id].risk_level if x.transaction_id in ras else None,
                      "score":ras[x.transaction_id].final_score if x.transaction_id in ras else None} for x in rows],
            "page":page,"page_size":page_size,"total":total}

@app.get("/transactions/{transaction_id}")
def transaction_detail(transaction_id:int,db:Session=Depends(get_db)):
    tx=db.scalar(select(Transaction).where(Transaction.transaction_id==transaction_id))
    if not tx: raise HTTPException(404,"Transaction not found")
    ra=db.scalar(select(RiskAssessment).where(RiskAssessment.transaction_id==transaction_id))
    alert=db.scalar(select(Alert).where(Alert.transaction_id==transaction_id))
    case=db.scalar(select(InvestigationCase).where(InvestigationCase.transaction_id==transaction_id))
    return {"transaction":transaction_payload(tx),"assessment":assessment_payload(ra),
            "workflow":{"alert_id":alert.alert_id if alert else None,"alert_status":alert.status if alert else None,
                        "case_id":case.case_id if case else None,"case_status":case.status if case else None}}

@app.post("/analyse")
def analyse(req:AnalyseRequest,db:Session=Depends(get_db)):
    tx=db.scalar(select(Transaction).where(Transaction.transaction_id==req.transaction_id))
    if not tx: raise HTTPException(404,"Transaction not found")
    try: analyse_transaction(db,tx)
    except (RuntimeError,KeyError) as e: raise HTTPException(409,str(e))
    return transaction_detail(tx.transaction_id,db)

@app.get("/alerts")
def alerts(status:str="Open",db:Session=Depends(get_db)):
    q=select(Alert).order_by(desc(Alert.updated_at), desc(Alert.created_at))
    if status.lower() != "all": q=q.where(func.lower(Alert.status)==status.lower())
    rows=db.scalars(q).all(); ids=[a.transaction_id for a in rows]
    txs={t.transaction_id:t for t in db.scalars(select(Transaction).where(Transaction.transaction_id.in_(ids))).all()} if ids else {}
    ras={r.transaction_id:r for r in db.scalars(select(RiskAssessment).where(RiskAssessment.transaction_id.in_(ids))).all()} if ids else {}
    return [{"alert_id":a.alert_id,"transaction_id":a.transaction_id,"severity":a.severity,"status":a.status,"disposition":a.disposition,
             "created_at":a.created_at.isoformat(),"updated_at":a.updated_at.isoformat(),
             "amount":txs[a.transaction_id].amount if a.transaction_id in txs else None,
             "score":ras[a.transaction_id].final_score if a.transaction_id in ras else None} for a in rows]

@app.get("/alerts/summary")
def alert_summary(db:Session=Depends(get_db)):
    counts=dict(db.execute(select(Alert.status,func.count(Alert.id)).group_by(Alert.status)).all())
    return {"counts":{
        "Open":int(counts.get("Open",0)),
        "Acknowledged":int(counts.get("Acknowledged",0)),
        "Escalated":int(counts.get("Escalated",0)),
        "Closed":int(counts.get("Closed",0)),
        "All":int(sum(counts.values())),
    }}

@app.post("/alerts/{alert_id}/action")
def alert_action(alert_id:str,body:AlertAction,db:Session=Depends(get_db)):
    a=db.scalar(select(Alert).where(Alert.alert_id==alert_id))
    if not a: raise HTTPException(404,"Alert not found")
    if body.action == "acknowledge": a.status="Acknowledged"; a.disposition="Under analyst review"
    elif body.action == "dismiss": a.status="Closed"; a.disposition="Dismissed by analyst"
    else:
        a.status="Escalated"; a.disposition="Escalated to investigation"
        if not db.scalar(select(InvestigationCase).where(InvestigationCase.transaction_id==a.transaction_id)):
            db.add(InvestigationCase(case_id=f"CASE-{a.transaction_id}",transaction_id=a.transaction_id,priority=a.severity,status="New"))
    db.commit(); return {"ok":True}

@app.get("/cases")
def cases(status:str="active",db:Session=Depends(get_db)):
    q=select(InvestigationCase).order_by(desc(InvestigationCase.created_at))
    if status == "active": q=q.where(InvestigationCase.status.not_in(["Resolved","Closed"]))
    rows=db.scalars(q).all(); ids=[c.transaction_id for c in rows]
    ras={r.transaction_id:r for r in db.scalars(select(RiskAssessment).where(RiskAssessment.transaction_id.in_(ids))).all()} if ids else {}
    return [{"case_id":c.case_id,"transaction_id":c.transaction_id,"status":c.status,"priority":c.priority,"resolution":c.resolution,
             "score":ras[c.transaction_id].final_score if c.transaction_id in ras else None,"created_at":c.created_at.isoformat()} for c in rows]

@app.get("/cases/{case_id}")
def case_detail(case_id:str,db:Session=Depends(get_db)):
    c=db.scalar(select(InvestigationCase).where(InvestigationCase.case_id==case_id))
    if not c: raise HTTPException(404,"Case not found")
    tx=db.scalar(select(Transaction).where(Transaction.transaction_id==c.transaction_id))
    ra=db.scalar(select(RiskAssessment).where(RiskAssessment.transaction_id==c.transaction_id))
    notes=db.scalars(select(CaseNote).where(CaseNote.case_id==case_id).order_by(CaseNote.created_at)).all()
    return {"case":{"case_id":c.case_id,"transaction_id":c.transaction_id,"status":c.status,"priority":c.priority,"resolution":c.resolution,
                    "created_at":c.created_at.isoformat()},"transaction":transaction_payload(tx),"assessment":assessment_payload(ra),
            "notes":[{"author":n.author,"body":n.body,"created_at":n.created_at.isoformat()} for n in notes]}

@app.patch("/cases/{case_id}/status")
def status(case_id:str,body:CaseStatusUpdate,db:Session=Depends(get_db)):
    c=db.scalar(select(InvestigationCase).where(InvestigationCase.case_id==case_id))
    if not c: raise HTTPException(404,"Case not found")
    c.status=body.status; db.commit(); return {"ok":True}

@app.patch("/cases/{case_id}/resolution")
def resolution(case_id:str,body:CaseResolutionUpdate,db:Session=Depends(get_db)):
    c=db.scalar(select(InvestigationCase).where(InvestigationCase.case_id==case_id))
    if not c: raise HTTPException(404,"Case not found")
    c.resolution=body.resolution; c.status="Resolved"; db.commit(); return {"ok":True}

@app.post("/cases/{case_id}/notes")
def note(case_id:str,body:NoteCreate,db:Session=Depends(get_db)):
    if not db.scalar(select(InvestigationCase).where(InvestigationCase.case_id==case_id)): raise HTTPException(404,"Case not found")
    db.add(CaseNote(case_id=case_id,body=body.body,author=body.author)); db.commit(); return {"ok":True}

class UrlScanRequest(BaseModel): url:str
@app.get('/url/model')
def url_model(): return url_readiness()
@app.post('/url/scan')
def url_scan(body:UrlScanRequest):
    try: return scan_url(body.url)
    except ValueError as e: raise HTTPException(422, str(e))
    except RuntimeError as e: raise HTTPException(409, str(e))

def _heldout_start_dt(db: Session):
    total=db.scalar(select(func.count(Transaction.id))) or 0
    if not total: return None
    offset=min(total-1,int(total*.85))
    return db.scalar(select(Transaction.transaction_dt).order_by(Transaction.transaction_dt).offset(offset).limit(1))

def _evaluation_outcome_expr():
    predicted=RiskAssessment.risk_level.in_(["Review","Automatic case"])
    return case(
        (predicted & Transaction.is_fraud.is_(True), "true_positive"),
        (predicted & Transaction.is_fraud.is_(False), "false_positive"),
        (~predicted & Transaction.is_fraud.is_(True), "false_negative"),
        else_="true_negative",
    )

@app.get('/evaluation/next')
def evaluation_next(mode:str='random',db:Session=Depends(get_db)):
    start_dt=_heldout_start_dt(db)
    if start_dt is None: raise HTTPException(409,'No held-out evaluation transactions available')
    mode=mode.lower().strip()
    if mode in {'true_positive','true_negative','false_positive','false_negative'}:
        q=(select(Transaction).join(RiskAssessment,RiskAssessment.transaction_id==Transaction.transaction_id)
           .where(Transaction.transaction_dt>=start_dt,_evaluation_outcome_expr()==mode)
           .order_by(func.random()).limit(1))
        tx=db.scalar(q)
        if not tx: raise HTTPException(409,f'No assessed {mode.replace("_"," ")} is available yet. Analyse more held-out transactions first.')
        ra=db.scalar(select(RiskAssessment).where(RiskAssessment.transaction_id==tx.transaction_id))
    else:
        q=select(Transaction).where(Transaction.transaction_dt>=start_dt)
        if mode=='fraud': q=q.where(Transaction.is_fraud.is_(True))
        elif mode=='legitimate': q=q.where(Transaction.is_fraud.is_(False))
        elif mode!='random': raise HTTPException(422,'Unsupported evaluation mode')
        tx=db.scalar(q.order_by(func.random()).limit(1))
        if not tx: raise HTTPException(409,'No matching held-out evaluation transaction is available')
        ra=analyse_transaction(db,tx)
    return {'transaction':transaction_payload(tx),'assessment':assessment_payload(ra),'historical_outcome_hidden':True,'scenario':mode}

@app.get('/evaluation/{transaction_id}/reveal')
def evaluation_reveal(transaction_id:int,db:Session=Depends(get_db)):
    tx=db.scalar(select(Transaction).where(Transaction.transaction_id==transaction_id)); ra=db.scalar(select(RiskAssessment).where(RiskAssessment.transaction_id==transaction_id))
    if not tx or not ra: raise HTTPException(404,'Evaluation transaction not assessed')
    pred=ra.risk_level in ['Review','Automatic case']; truth=bool(tx.is_fraud)
    outcome='True Positive' if pred and truth else 'False Positive' if pred else 'False Negative' if truth else 'True Negative'
    return {'ground_truth':truth,'outcome':outcome}

def _psi(reference:list[float], current:list[float], bins:int=10):
    if not reference or not current: return None
    edges=[i*(100.0/bins) for i in range(bins+1)]
    def proportions(values):
        counts=[0]*bins
        for value in values:
            idx=min(bins-1,max(0,int(float(value)//(100.0/bins))))
            counts[idx]+=1
        total=len(values)
        return [max(c/total,1e-6) for c in counts]
    ref=proportions(reference); cur=proportions(current)
    return sum((c-r)*math.log(c/r) for r,c in zip(ref,cur))

@app.get('/monitoring/drift')
def drift_monitor(db:Session=Depends(get_db)):
    rows=db.execute(select(RiskAssessment.final_score,Transaction.transaction_dt)
        .join(Transaction,Transaction.transaction_id==RiskAssessment.transaction_id)
        .order_by(Transaction.transaction_dt)).all()
    if len(rows)<100:
        return {'status':'insufficient_data','assessed_rows':len(rows),'minimum_rows':100,
                'scope':'Offline replay monitoring only. No live production stream is connected.'}
    split=len(rows)//2
    reference=[float(r[0]) for r in rows[:split]]; current=[float(r[0]) for r in rows[split:]]
    psi=float(_psi(reference,current) or 0.0)
    status='stable' if psi<0.1 else 'watch' if psi<0.25 else 'shift_detected'
    return {'status':status,'psi':psi,'reference_rows':len(reference),'current_rows':len(current),
            'reference_mean_score':sum(reference)/len(reference),'current_mean_score':sum(current)/len(current),
            'method':'Population Stability Index across 10 fixed probability bands',
            'scope':'Offline replay monitoring only. No live production stream is connected.'}

