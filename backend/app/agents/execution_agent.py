from datetime import datetime
from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.models.audit_log import AuditLog
from app.services.razorpay_client import create_payment_link

SKIP_ACTIONS = {"no_action_exhausted", "escalate_human_review", "no_contact_opted_out"}

LINK_REQUIRED_ACTIONS = {
    "auto_retry", "retry_delayed", "retry_immediate", "mandate_retry_sequence",
    "send_payment_link", "request_card_update", "gentle_reminder",
    "firm_reminder", "escalation_reminder",
}


def run_execution(db: Session, transactions: list[Transaction]) -> dict:
    link_created_count = 0
    skipped_count = 0
    already_pending_count = 0

    total = len(transactions)
    for i, txn in enumerate(transactions, 1):
        if i % 25 == 0 or i == 1:
            print(f"⏳ Execution progress: {i}/{total}", flush=True)

        if txn.decided_action in SKIP_ACTIONS:
            skipped_count += 1
            continue

        if txn.status == "recovering" and txn.razorpay_payment_link_id:
            already_pending_count += 1
            continue

        if txn.decided_action in LINK_REQUIRED_ACTIONS:
            _create_real_recovery_link(db, txn)
            link_created_count += 1
        else:
            _log(db, txn, f"No execution handler for action '{txn.decided_action}'. Skipped.")
            skipped_count += 1

        db.commit()

    return {
        "link_created_count": link_created_count,
        "already_pending_count": already_pending_count,
        "skipped_count": skipped_count,
    }


def _create_real_recovery_link(db: Session, txn: Transaction):
    customer = txn.customer
    try:
        link = create_payment_link(
            amount=txn.amount,
            customer_name=customer.name if customer else "Customer",
            customer_email=customer.email if customer else "test@example.com",
            customer_phone=customer.phone if customer else "9999999999",
            description=f"RAAHI recovery — {txn.record_type} {txn.id}",
        )

        txn.attempts_made += 1
        txn.status = "recovering"
        txn.razorpay_payment_link_id = link.get("id")
        txn.payment_link_url = link.get("short_url")

        _log(db, txn, f"✅ Real Razorpay payment link created: {link.get('short_url')}. "
                        f"Status set to 'recovering' — awaiting real payment confirmation via webhook. "
                        f"Attempt {txn.attempts_made}/{txn.max_attempts}.")

    except Exception as e:
        _log(db, txn, f"❌ Payment link creation failed: {str(e)[:150]}")


def _log(db: Session, txn: Transaction, reasoning: str):
    log = AuditLog(
        transaction_id=txn.id,
        stage="execution",
        summary=f"Execution: {txn.decided_action} → {txn.status}",
        reasoning=reasoning,
        timestamp=datetime.utcnow(),
    )
    db.add(log)