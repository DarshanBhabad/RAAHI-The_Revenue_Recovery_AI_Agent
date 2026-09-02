"""
Shared pytest fixtures. Uses an in-memory SQLite DB, completely isolated
from the real Supabase database — safe to run repeatedly without touching
production/demo data.
"""
import uuid
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.models.customer import Customer
from app.models.transaction import Transaction


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def make_customer(db, **overrides):
    defaults = dict(
        id=f"cust_test_{uuid.uuid4().hex[:12]}",
        name="Test Customer",
        phone="+919845123670",
        email="test@example.com",
        ltv_segment="standard",
        opted_out=False,
    )
    defaults.update(overrides)
    c = Customer(**defaults)
    db.add(c)
    db.flush()
    return c


def make_txn(db, customer, **overrides):
    now = datetime.utcnow()
    defaults = dict(
        id=f"txn_test_{uuid.uuid4().hex[:12]}",
        merchant_id="merch_test",
        customer_id=customer.id,
        record_type="payment",
        amount=1500.0,
        status="at_risk",
        failure_reason_code="insufficient_funds",
        root_cause="insufficient_funds",
        diagnosis_confidence=0.85,
        decided_action="retry_delayed",
        channel="sms",
        attempts_made=0,
        max_attempts=3,
        recovered_amount=0.0,
        is_exception=False,
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    t = Transaction(**defaults)
    db.add(t)
    db.flush()
    return t