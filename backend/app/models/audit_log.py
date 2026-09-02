from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from datetime import datetime
from app.db.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(String, ForeignKey("transactions.id"), nullable=False)

    stage = Column(String, nullable=False)   # detection | diagnosis | decision | guardrail | execution
    summary = Column(String, nullable=False)  # short one-line result
    reasoning = Column(Text, nullable=True)   # full explanation text
    payload = Column(Text, nullable=True)     # JSON string snapshot of inputs/outputs

    timestamp = Column(DateTime, default=datetime.utcnow)
    violation_code = Column(String, nullable=True)