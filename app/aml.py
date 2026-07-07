from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app.models import Transaction

def aml_profile(db:Session, transaction_id:int):
    tx=db.scalar(select(Transaction).where(Transaction.transaction_id==transaction_id))
    if not tx: return None
    start=max(0,tx.transaction_dt-86400)
    q=select(Transaction).where(Transaction.card1==tx.card1,Transaction.transaction_dt>=start,Transaction.transaction_dt<=tx.transaction_dt)
    rows=db.scalars(q).all(); count=len(rows); total=sum(r.amount for r in rows); avg=total/max(count,1)
    signals=[]; score=0
    if count>=8: signals.append({'signal':'24h velocity','value':count,'weight':25}); score+=25
    if total>=5000: signals.append({'signal':'24h aggregate value','value':round(total,2),'weight':25}); score+=25
    if avg and tx.amount>=3*avg and count>2: signals.append({'signal':'amount vs recent average','value':round(tx.amount/avg,2),'weight':25}); score+=25
    small=sum(1 for r in rows if 900<=r.amount<=1100)
    if small>=3: signals.append({'signal':'repeated similar-value activity','value':small,'weight':25}); score+=25
    return {'transaction_id':transaction_id,'score':score,'level':'High' if score>=75 else 'Review' if score>=50 else 'Monitor' if score>=25 else 'Low','signals':signals,'window_transactions':count,'window_value':round(total,2),'method':'transparent behavioral analytics; not a trained AML classifier'}
