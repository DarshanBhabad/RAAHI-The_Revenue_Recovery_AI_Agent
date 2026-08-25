from datetime import datetime
from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.models.audit_log import AuditLog
from app.services.razorpay_client import client as rzp_client


def check_pending_links(db: Session) -> dict:
    """
    Polls Razorpay directly for any payment links still marked 'recovering'.
    This is a safety net alongside webhooks — catches anything a webhook missed.
    """
    pending = (
        db.query(Transaction)
        .filter(Transaction.status == "recovering")
        .filter(Transaction.razorpay_payment_link_id.isnot(None))
        .all()
    )

    updated = 0
    for txn in pending:
        try:
            link = rzp_client.payment_link.fetch(txn.razorpay_payment_link_id)
            if link.get("status") == "paid":
                txn.status = "recovered"
                txn.recovered_amount = txn.amount
                txn.outcome_source = "real_verified"
                db.add(AuditLog(
                    transaction_id=txn.id, stage="execution",
                    summary="Recovered (confirmed via polling)",
                    reasoning=f"Payment link {txn.razorpay_payment_link_id} confirmed paid on poll check.",
                    timestamp=datetime.utcnow(),
                ))
                updated += 1
        except Exception as e:
            print(f"⚠️ Poll check failed for {txn.id}: {str(e)[:100]}", flush=True)

    db.commit()
    return {"checked": len(pending), "newly_recovered": updated}