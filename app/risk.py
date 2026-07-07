import json
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models import Transaction, RiskAssessment, InvestigationCase, Alert
from app.ml import predict, tier_for_probability, TIER_AUTOMATIC_CASE, TIER_REVIEW


def evidence_scores(db: Session, tx: Transaction):
    hist = db.scalars(select(Transaction).where(Transaction.card1 == tx.card1, Transaction.transaction_dt < tx.transaction_dt).order_by(Transaction.transaction_dt.desc()).limit(100)).all() if tx.card1 else []
    reasons, behavioural, velocity = [], 0.0, 0.0
    if len(hist) >= 10:
        mean = sum(h.amount for h in hist) / len(hist)
        if mean > 0 and tx.amount > mean * 5:
            behavioural = min(100, 50 + (tx.amount / mean - 5) * 5)
            reasons.append(f"Amount is {tx.amount/mean:.1f}× the recent mean for this anonymized card proxy.")
        known = {h.device_info for h in hist if h.device_info}
        if tx.device_info and known and tx.device_info not in known:
            behavioural = max(behavioural, 55)
            reasons.append("Device information is unseen in this proxy's recent imported history.")
    recent = [h for h in hist if 0 <= tx.transaction_dt - h.transaction_dt <= 300]
    if len(recent) >= 3:
        velocity = min(100, 35 + len(recent) * 10)
        reasons.append(f"{len(recent)+1} transactions occurred within five minutes.")
    network = 0.0
    if tx.device_info:
        cards = db.scalar(select(func.count(func.distinct(Transaction.card1))).where(Transaction.device_info == tx.device_info, Transaction.card1.is_not(None))) or 0
        if cards >= 4:
            network = min(100, 25 + cards * 5)
            reasons.append(f"Device proxy is linked to {cards} distinct card proxies in imported real data.")
    return behavioural, velocity, network, reasons


def analyse_transaction(db: Session, tx: Transaction, force=False):
    existing = db.scalar(select(RiskAssessment).where(RiskAssessment.transaction_id == tx.transaction_id))
    if existing and not force:
        return existing
    if existing and force:
        db.delete(existing)
        db.flush()
    prob, anomaly, meta = predict(tx.transaction_id)
    level, action, threshold = tier_for_probability(prob, meta)
    behavioural, velocity, network, reasons = evidence_scores(db, tx)
    if prob >= threshold:
        reasons.insert(0, f"V3 probability {prob:.2%} crossed the {level.lower()} operating threshold {threshold:.2%}.")
    else:
        reasons.insert(0, f"V3 probability {prob:.2%} remained below the monitor threshold {threshold:.2%}.")
    if anomaly >= .8:
        reasons.append("Transaction is in the extreme anomaly tail of the V3 validation distribution.")
    if len(reasons) == 1:
        reasons.append("No strong corroborating evidence was found in imported transaction history.")
    score = prob * 100
    ra = RiskAssessment(transaction_id=tx.transaction_id, fraud_probability=score, anomaly_score=anomaly*100,
        behavioural_score=behavioural, velocity_score=velocity, network_score=network, final_score=score,
        risk_level=level, reasons_json=json.dumps(reasons), model_version=meta["version"])
    db.add(ra)
    db.flush()
    if level in {TIER_REVIEW, TIER_AUTOMATIC_CASE} and not db.scalar(select(Alert).where(Alert.transaction_id == tx.transaction_id)):
        db.add(Alert(alert_id=f"ALT-{tx.transaction_id}", transaction_id=tx.transaction_id, severity=level))
    if level == TIER_AUTOMATIC_CASE and not db.scalar(select(InvestigationCase).where(InvestigationCase.transaction_id == tx.transaction_id)):
        db.add(InvestigationCase(case_id=f"CASE-{tx.transaction_id}", transaction_id=tx.transaction_id, priority=level))
    db.commit()
    db.refresh(ra)
    return ra
