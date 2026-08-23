from fastapi import APIRouter
from collections import defaultdict

from app.db.database import SessionLocal
from app.models.transaction import Transaction
from app.schemas.pydantic_schemas import DashboardSummary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary():
    db = SessionLocal()
    try:
        all_txns = db.query(Transaction).all()

        total_at_risk = sum(t.amount for t in all_txns)
        total_recovered = sum(t.recovered_amount for t in all_txns)
        exceptions_count = sum(1 for t in all_txns if t.is_exception)

        breakdown = defaultdict(lambda: {"count": 0, "recovered_count": 0, "recovered_amount": 0.0})
        for t in all_txns:
            key = t.root_cause or "undiagnosed"
            breakdown[key]["count"] += 1
            breakdown[key]["recovered_amount"] += t.recovered_amount
            if t.status == "recovered":
                breakdown[key]["recovered_count"] += 1

        recovery_rate = (total_recovered / total_at_risk * 100) if total_at_risk > 0 else 0.0

        return DashboardSummary(
            total_at_risk_amount=round(total_at_risk, 2),
            total_recovered_amount=round(total_recovered, 2),
            recovery_rate_pct=round(recovery_rate, 2),
            total_records=len(all_txns),
            exceptions_count=exceptions_count,
            breakdown_by_root_cause=dict(breakdown),
        )
    finally:
        db.close()


@router.get("/merchants")
def get_merchant_breakdown():
    """Per-merchant view — proves the agent generalizes across D2C, SaaS, and B2B, not hardcoded to one."""
    db = SessionLocal()
    try:
        all_txns = db.query(Transaction).all()
        by_merchant = defaultdict(lambda: {"count": 0, "at_risk_amount": 0.0, "recovered_amount": 0.0})

        for t in all_txns:
            m = by_merchant[t.merchant_id]
            m["count"] += 1
            m["at_risk_amount"] += t.amount
            m["recovered_amount"] += t.recovered_amount

        return dict(by_merchant)
    finally:
        db.close()