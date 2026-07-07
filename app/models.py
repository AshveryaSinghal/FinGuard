from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, Boolean, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Transaction(Base):
    __tablename__ = "transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    transaction_dt: Mapped[int] = mapped_column(Integer, index=True)
    amount: Mapped[float] = mapped_column(Float)
    product_cd: Mapped[str | None] = mapped_column(String(8))
    card1: Mapped[int | None] = mapped_column(Integer, index=True)
    card2: Mapped[float | None] = mapped_column(Float)
    card3: Mapped[float | None] = mapped_column(Float)
    card4: Mapped[str | None] = mapped_column(String(32))
    card5: Mapped[float | None] = mapped_column(Float)
    card6: Mapped[str | None] = mapped_column(String(32))
    addr1: Mapped[float | None] = mapped_column(Float)
    addr2: Mapped[float | None] = mapped_column(Float)
    dist1: Mapped[float | None] = mapped_column(Float)
    p_emaildomain: Mapped[str | None] = mapped_column(String(128))
    r_emaildomain: Mapped[str | None] = mapped_column(String(128))
    device_type: Mapped[str | None] = mapped_column(String(32))
    device_info: Mapped[str | None] = mapped_column(String(256))
    is_fraud: Mapped[bool] = mapped_column(Boolean, index=True)
    source: Mapped[str] = mapped_column(String(32), default="IEEE-CIS")

class RiskAssessment(Base):
    __tablename__ = "risk_assessments"
    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.transaction_id"), unique=True, index=True)
    fraud_probability: Mapped[float] = mapped_column(Float)
    anomaly_score: Mapped[float] = mapped_column(Float)
    behavioural_score: Mapped[float] = mapped_column(Float)
    velocity_score: Mapped[float] = mapped_column(Float)
    network_score: Mapped[float] = mapped_column(Float)
    final_score: Mapped[float] = mapped_column(Float, index=True)
    risk_level: Mapped[str] = mapped_column(String(32), index=True)
    reasons_json: Mapped[str] = mapped_column(Text)
    model_version: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(primary_key=True)
    alert_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.transaction_id"), unique=True, index=True)
    severity: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), default="Open", index=True)
    disposition: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class InvestigationCase(Base):
    __tablename__ = "investigation_cases"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.transaction_id"), unique=True)
    status: Mapped[str] = mapped_column(String(32), default="New", index=True)
    priority: Mapped[str] = mapped_column(String(32))
    resolution: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CaseNote(Base):
    __tablename__ = "case_notes"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[str] = mapped_column(ForeignKey("investigation_cases.case_id"), index=True)
    author: Mapped[str] = mapped_column(String(80), default="Investigator")
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class ModelMetadata(Base):
    __tablename__ = "model_metadata"
    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[str] = mapped_column(String(64), unique=True)
    trained_at: Mapped[datetime] = mapped_column(DateTime)
    metrics_json: Mapped[str] = mapped_column(Text)
    threshold: Mapped[float] = mapped_column(Float)
    dataset_name: Mapped[str] = mapped_column(String(128))

Index("ix_tx_card_time", Transaction.card1, Transaction.transaction_dt)
