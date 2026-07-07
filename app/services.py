from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session
from app.models import Transaction, RiskAssessment, InvestigationCase, Alert

def dashboard(db: Session):
    total = db.scalar(select(func.count(Transaction.id))) or 0
    assessed = db.scalar(select(func.count(RiskAssessment.id))) or 0
    open_alerts = db.scalar(select(func.count(Alert.id)).where(Alert.status == "Open")) or 0
    active_cases = db.scalar(select(func.count(InvestigationCase.id)).where(InvestigationCase.status.not_in(["Resolved", "Closed"]))) or 0
    levels = dict(db.execute(select(RiskAssessment.risk_level, func.count()).group_by(RiskAssessment.risk_level)).all())
    recent = db.execute(select(RiskAssessment.transaction_id, RiskAssessment.created_at, RiskAssessment.final_score, RiskAssessment.risk_level).order_by(desc(RiskAssessment.created_at)).limit(8)).all()
    return {"transactions": total, "assessed": assessed, "open_alerts": open_alerts, "active_cases": active_cases,
            "risk_distribution": levels, "recent_assessments": [{"transaction_id":r[0],"at":r[1].isoformat(),"score":r[2],"risk_level":r[3]} for r in recent]}
