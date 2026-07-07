import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.ml import tier_for_probability
from app.database import Base
from app.models import Transaction, InvestigationCase
import app.risk as risk_module

META = {
    "version": "test-fixture-v3",
    "product_thresholds": {
        "monitor": {"threshold": 0.04820418357849121},
        "review": {"threshold": 0.138283371925354},
        "automatic_case": {"threshold": 0.9652385115623474},
    },
}


def test_artifact_threshold_tiers():
    assert tier_for_probability(.01, META)[0] == "Low"
    assert tier_for_probability(.10, META)[0] == "Monitor"
    assert tier_for_probability(.6317, META)[0] == "Review"
    assert tier_for_probability(.99, META)[0] == "Automatic case"


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def _make_tx(session, transaction_id):
    tx = Transaction(
        transaction_id=transaction_id, transaction_dt=1000, amount=100.0,
        product_cd="W", is_fraud=False, source="IEEE-CIS",
    )
    session.add(tx)
    session.commit()
    session.refresh(tx)
    return tx


def _stub_predict(probability):
    def _predict(_transaction_id):
        return probability, 0.0, META
    return _predict


def test_automatic_case_creates_exactly_one_investigation_case(monkeypatch, db_session):
    monkeypatch.setattr(risk_module, "predict", _stub_predict(0.99))
    tx = _make_tx(db_session, 1)
    ra = risk_module.analyse_transaction(db_session, tx)
    assert ra.risk_level == "Automatic case"
    cases = db_session.scalars(select(InvestigationCase)).all()
    assert len(cases) == 1
    assert cases[0].transaction_id == tx.transaction_id


def test_automatic_case_does_not_duplicate_on_reanalysis(monkeypatch, db_session):
    monkeypatch.setattr(risk_module, "predict", _stub_predict(0.99))
    tx = _make_tx(db_session, 2)
    risk_module.analyse_transaction(db_session, tx)
    risk_module.analyse_transaction(db_session, tx, force=True)
    cases = db_session.scalars(
        select(InvestigationCase).where(InvestigationCase.transaction_id == tx.transaction_id)
    ).all()
    assert len(cases) == 1


def test_review_tier_does_not_auto_create_case(monkeypatch, db_session):
    monkeypatch.setattr(risk_module, "predict", _stub_predict(0.6317))
    tx = _make_tx(db_session, 3)
    ra = risk_module.analyse_transaction(db_session, tx)
    assert ra.risk_level == "Review"
    assert db_session.scalars(select(InvestigationCase)).all() == []


@pytest.mark.parametrize("probability,expected_level", [(0.10, "Monitor"), (0.01, "Low")])
def test_monitor_and_low_tiers_do_not_auto_create_case(monkeypatch, db_session, probability, expected_level):
    monkeypatch.setattr(risk_module, "predict", _stub_predict(probability))
    tx = _make_tx(db_session, 4)
    ra = risk_module.analyse_transaction(db_session, tx)
    assert ra.risk_level == expected_level
    assert db_session.scalars(select(InvestigationCase)).all() == []


def test_review_tier_creates_open_alert(monkeypatch, db_session):
    from app.models import Alert
    monkeypatch.setattr(risk_module, "predict", _stub_predict(0.6317))
    tx = _make_tx(db_session, 30)
    risk_module.analyse_transaction(db_session, tx)
    alerts = db_session.scalars(select(Alert)).all()
    assert len(alerts) == 1
    assert alerts[0].severity == "Review"
    assert alerts[0].status == "Open"


def test_low_tier_does_not_create_alert(monkeypatch, db_session):
    from app.models import Alert
    monkeypatch.setattr(risk_module, "predict", _stub_predict(0.01))
    tx = _make_tx(db_session, 31)
    risk_module.analyse_transaction(db_session, tx)
    assert db_session.scalars(select(Alert)).all() == []
