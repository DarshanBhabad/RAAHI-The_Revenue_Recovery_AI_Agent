from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, index=True)
    merchant_id = Column(String, index=True, nullable=False)
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False)

    record_type = Column(String, nullable=False)        # "payment" | "subscription" | "invoice"
    amount = Column(Float, nullable=False)
    currency = Column(String, default="INR")

    status = Column(String, default="at_risk")           # at_risk | recovering | recovered | exception
    failure_reason_code = Column(String, nullable=True)  # e.g. insufficient_funds, issuer_unavailable

    root_cause = Column(String, nullable=True)
    diagnosis_confidence = Column(Float, nullable=True)

    decided_action = Column(String, nullable=True)       # e.g. retry_delayed, send_payment_link
    channel = Column(String, nullable=True)               # sms | whatsapp | email | auto_retry

    attempts_made = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)

    recovered_amount = Column(Float, default=0.0)
    is_exception = Column(Boolean, default=False)
    exception_reason = Column(String, nullable=True)

    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer")