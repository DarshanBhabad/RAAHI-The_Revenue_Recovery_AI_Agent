from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TransactionOut(BaseModel):
    id: str
    merchant_id: str
    customer_id: str
    record_type: str
    amount: float
    status: str
    root_cause: Optional[str] = None
    diagnosis_confidence: Optional[float] = None
    decided_action: Optional[str] = None
    channel: Optional[str] = None
    attempts_made: int
    recovered_amount: float
    is_exception: bool
    exception_reason: Optional[str] = None
    voice_message_url: Optional[str] = None
    voice_message_text: Optional[str] = None
    created_at: datetime
    customer_reply_text: Optional[str] = None
    promised_pay_date: Optional[datetime] = None
    promise_confidence: Optional[float] = None
    promise_broken: Optional[bool] = None

    class Config:
        from_attributes = True


class AuditLogOut(BaseModel):
    stage: str
    summary: str
    reasoning: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True


class DashboardSummary(BaseModel):
    total_at_risk_amount: float
    total_recovered_amount: float
    recovery_rate_pct: float
    total_records: int
    exceptions_count: int
    breakdown_by_root_cause: dict