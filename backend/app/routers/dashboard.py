import json
import os
from fastapi import APIRouter
from collections import defaultdict

from app.db.database import SessionLocal
from app.models.transaction import Transaction
from app.models.audit_log import AuditLog
from app.models.customer import Customer
from app.schemas.pydantic_schemas import DashboardSummary
from app.services.cache_service import get_cache_metrics

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

MERCHANT_ID = "merch_real_001"


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary():
    db = SessionLocal()
    try:
        all_txns = db.query(Transaction).filter(
            Transaction.merchant_id == MERCHANT_ID,
            Transaction.status.notin_(["checkout_pending"]),
        ).all()

        total_at_risk = sum(t.amount for t in all_txns)
        total_recovered = sum(t.recovered_amount for t in all_txns)
        still_at_risk = sum(t.amount for t in all_txns if t.status not in ("recovered", "partially_recovered"))
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
            total_at_risk_amount=round(still_at_risk, 2),
            total_recovered_amount=round(total_recovered, 2),
            recovery_rate_pct=round(recovery_rate, 2),
            total_records=len(all_txns),
            exceptions_count=exceptions_count,
            breakdown_by_root_cause=dict(breakdown),
        )
    finally:
        db.close()


@router.get("/llm-cache-metrics")
def llm_cache_metrics():
    return get_cache_metrics()


@router.get("/voice-messages")
def get_voice_messages():
    db = SessionLocal()
    try:
        txns = (
            db.query(Transaction)
            .filter(
                Transaction.merchant_id == MERCHANT_ID,
                Transaction.voice_message_url.isnot(None),
            )
            .limit(20)
            .all()
        )
        return [
            {
                "id": t.id,
                "amount": t.amount,
                "root_cause": t.root_cause,
                "voice_message_text": t.voice_message_text,
                "voice_message_url": t.voice_message_url,
            }
            for t in txns
        ]
    finally:
        db.close()


@router.get("/channel-distribution")
def get_channel_distribution():
    db = SessionLocal()
    try:
        txns = (
            db.query(Transaction)
            .filter(
                Transaction.merchant_id == MERCHANT_ID,
                Transaction.channel.isnot(None),
            )
            .all()
        )
        counts = {}
        for t in txns:
            counts[t.channel] = counts.get(t.channel, 0) + 1
        return counts
    finally:
        db.close()


@router.get("/outcome-source-breakdown")
def get_outcome_source_breakdown():
    db = SessionLocal()
    try:
        txns = db.query(Transaction).filter(Transaction.merchant_id == MERCHANT_ID).all()
        counts = {}
        for t in txns:
            src = t.outcome_source or "unset"
            counts[src] = counts.get(src, 0) + 1
        return counts
    finally:
        db.close()


@router.get("/ml-model-metrics")
def get_ml_model_metrics():
    path = "app/ml/model_artifacts/metrics.json"
    if not os.path.exists(path):
        return {"message": "Model not yet trained"}
    with open(path) as f:
        return json.load(f)


@router.get("/recent-events")
def get_recent_events(limit: int = 15):
    db = SessionLocal()
    try:
        logs = (
            db.query(AuditLog)
            .order_by(AuditLog.timestamp.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "stage": l.stage,
                "summary": l.summary,
                "timestamp": l.timestamp.isoformat(),
            }
            for l in logs
        ]
    finally:
        db.close()


@router.get("/retry-timing-model")
def get_retry_timing_model():
    path = "app/ml/model_artifacts/retry_timing_recommendations.json"
    if not os.path.exists(path):
        return {"message": "Timing model not yet trained"}
    with open(path) as f:
        return json.load(f)


@router.get("/guardrail-activity")
def get_guardrail_activity():
    db = SessionLocal()
    try:
        txn_ids = [
            t.id
            for t in db.query(Transaction.id)
            .filter(Transaction.merchant_id == MERCHANT_ID)
            .all()
        ]
        logs = (
            db.query(AuditLog)
            .filter(AuditLog.stage == "guardrail", AuditLog.transaction_id.in_(txn_ids))
            .all()
        )

        verdict_counts = {"approved": 0, "modified": 0, "blocked": 0}
        reason_counts = {}

        for log in logs:
            summary_lower = log.summary.lower()
            if "approved" in summary_lower:
                verdict_counts["approved"] += 1
            elif "modified" in summary_lower:
                verdict_counts["modified"] += 1
                reasoning_lower = (log.reasoning or "").lower()
                if "dnd" in reasoning_lower:
                    reason_counts["DND window"] = reason_counts.get("DND window", 0) + 1
                elif "cooldown" in reasoning_lower:
                    reason_counts["Cooldown active"] = reason_counts.get("Cooldown active", 0) + 1
                elif "downtime" in reasoning_lower:
                    reason_counts["Real-time downtime"] = reason_counts.get("Real-time downtime", 0) + 1
            elif "blocked" in summary_lower:
                verdict_counts["blocked"] += 1
                reason_counts["Attempt limit reached"] = reason_counts.get("Attempt limit reached", 0) + 1

        return {
            "verdict_counts": verdict_counts,
            "deferral_reasons": reason_counts,
            "total_guardrail_checks": len(logs),
        }
    finally:
        db.close()


@router.post("/admin/reset-db")
def reset_database():
    """
    Wipes all transactions, audit logs, and customers.
    Use this to clear synthetic/demo data before going real-time.
    """
    db = SessionLocal()
    try:
        audit_deleted = db.query(AuditLog).delete()
        txn_deleted = db.query(Transaction).delete()
        cust_deleted = db.query(Customer).delete()
        db.commit()
        return {
            "status": "ok",
            "audit_logs_deleted": audit_deleted,
            "transactions_deleted": txn_deleted,
            "customers_deleted": cust_deleted,
        }
    except Exception as e:
        db.rollback()
        return {"status": "error", "detail": str(e)}
    finally:
        db.close()
