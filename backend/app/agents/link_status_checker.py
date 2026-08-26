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

def check_broken_promises(db: Session) -> dict:
    """
    Checks records with a promised_pay_date that has passed and still aren't
    recovered — flags them as broken promises for stronger escalation.
    """
    now = datetime.utcnow()
    overdue_promises = (
        db.query(Transaction)
        .filter(Transaction.promised_pay_date.isnot(None))
        .filter(Transaction.promised_pay_date < now)
        .filter(Transaction.status == "recovering")
        .filter(Transaction.promise_broken == False)  # noqa: E712
        .all()
    )

    for txn in overdue_promises:
        txn.promise_broken = True
        txn.decided_action = "escalation_reminder"  # override — broken promise = stronger action
        db.add(AuditLog(
            transaction_id=txn.id, stage="execution",
            summary="Promise-to-pay broken — escalating",
            reasoning=f"Customer promised payment by {txn.promised_pay_date.isoformat()} but "
                        f"payment not received. Escalating to firmer follow-up.",
            timestamp=now,
        ))

    db.commit()
    return {"broken_promises_found": len(overdue_promises)}