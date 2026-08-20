from datetime import datetime
from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.models.audit_log import AuditLog


# Records older than this are considered stale/still valid at-risk signals.
# (In a real system this would tie to webhook events; here we treat any
# record still sitting in "at_risk" status as a valid detection.)

def run_detection(db: Session, merchant_id: str | None = None) -> list[Transaction]:
    """
    Scans transactions and returns the ones confirmed as revenue-at-risk.
    Writes a detection-stage audit log entry for each.
    """
    query = db.query(Transaction).filter(Transaction.status == "at_risk")
    if merchant_id:
        query = query.filter(Transaction.merchant_id == merchant_id)

    at_risk_records = query.all()

    for txn in at_risk_records:
        summary = _build_summary(txn)

        log = AuditLog(
            transaction_id=txn.id,
            stage="detection",
            summary=summary,
            reasoning=(
                f"Record type '{txn.record_type}' with status 'at_risk' and "
                f"failure reason '{txn.failure_reason_code}' detected as revenue at risk. "
                f"Amount involved: ₹{txn.amount:,.2f}."
            ),
            timestamp=datetime.utcnow(),
        )
        db.add(log)

    db.commit()
    return at_risk_records


def _build_summary(txn: Transaction) -> str:
    if txn.record_type == "payment":
        return f"Failed payment detected — ₹{txn.amount:,.2f} ({txn.failure_reason_code})"
    elif txn.record_type == "subscription":
        return f"Failed subscription renewal detected — ₹{txn.amount:,.2f} ({txn.failure_reason_code})"
    elif txn.record_type == "invoice":
        return f"Overdue invoice detected — ₹{txn.amount:,.2f} ({txn.failure_reason_code})"
    return f"At-risk record detected — ₹{txn.amount:,.2f}"