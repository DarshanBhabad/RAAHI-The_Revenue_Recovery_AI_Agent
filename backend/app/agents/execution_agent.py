import random
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.models.audit_log import AuditLog
from app.services.razorpay_client import create_test_order, create_payment_link
from app.policies.recovery_probability import get_recovery_probability

RETRY_ACTIONS = {"auto_retry", "retry_delayed", "retry_immediate", "mandate_retry_sequence"}
LINK_ACTIONS = {"send_payment_link", "request_card_update", "gentle_reminder",
                "firm_reminder", "escalation_reminder"}
SKIP_ACTIONS = {"no_action_exhausted", "escalate_human_review", "no_contact_opted_out"}


def run_execution(db: Session, transactions: list[Transaction]) -> dict:
    recovered_count = 0
    failed_attempt_count = 0
    skipped_count = 0
    total_recovered_amount = 0.0

    for txn in transactions:
        if txn.decided_action in SKIP_ACTIONS:
            skipped_count += 1
            continue

        if txn.decided_action in RETRY_ACTIONS:
            _execute_retry(db, txn)
        elif txn.decided_action in LINK_ACTIONS:
            _execute_payment_link(db, txn)
        else:
            _log(db, txn, f"No execution handler for action '{txn.decided_action}'. Skipped.")
            skipped_count += 1
            continue

        if txn.status == "recovered":
            recovered_count += 1
            total_recovered_amount += txn.recovered_amount
        else:
            failed_attempt_count += 1

    db.commit()

    return {
        "recovered_count": recovered_count,
        "failed_attempt_count": failed_attempt_count,
        "skipped_count": skipped_count,
        "total_recovered_amount": round(total_recovered_amount, 2),
    }


def _execute_retry(db: Session, txn: Transaction):
    try:
        order = create_test_order(txn.amount, receipt=txn.id)
        api_note = f"Razorpay test order created: {order.get('id', 'unknown')}."
    except Exception as e:
        api_note = f"Razorpay order creation failed ({str(e)[:80]}); simulating outcome only."

    txn.attempts_made += 1
    probability = get_recovery_probability(txn.root_cause)
    success = random.random() < probability

    if success:
        txn.status = "recovered"
        txn.recovered_amount = txn.amount
        outcome_note = (f"Retry succeeded (modeled outcome, {probability:.0%} recovery "
                         f"probability for '{txn.root_cause}').")
    else:
        outcome_note = (f"Retry failed (modeled outcome, {probability:.0%} recovery "
                         f"probability for '{txn.root_cause}'). Will re-attempt next eligible cycle.")

    _log(db, txn, f"{api_note} {outcome_note} Attempt {txn.attempts_made}/{txn.max_attempts}.")


def _execute_payment_link(db: Session, txn: Transaction):
    customer = txn.customer
    try:
        link = create_payment_link(
            amount=txn.amount,
            customer_name=customer.name if customer else "Customer",
            customer_email=customer.email if customer else "test@example.com",
            customer_phone=customer.phone if customer else "9999999999",
            description=f"RAAHI recovery — {txn.record_type} {txn.id}",
        )
        api_note = f"Razorpay payment link created: {link.get('id', 'unknown')} ({link.get('short_url', 'n/a')})."
    except Exception as e:
        api_note = f"Payment link creation failed ({str(e)[:80]}); simulating outcome only."

    txn.attempts_made += 1
    probability = get_recovery_probability(txn.root_cause)
    success = random.random() < probability

    if success:
        txn.status = "recovered"
        txn.recovered_amount = txn.amount
        outcome_note = f"Customer completed payment via link (modeled outcome, {probability:.0%} probability)."
    else:
        txn.status = "recovering"
        outcome_note = f"Link sent, payment pending (modeled outcome, {probability:.0%} probability)."

    _log(db, txn, f"{api_note} {outcome_note} Channel: {txn.channel}.")


def _log(db: Session, txn: Transaction, reasoning: str):
    log = AuditLog(
        transaction_id=txn.id,
        stage="execution",
        summary=f"Execution: {txn.decided_action} → {txn.status}",
        reasoning=reasoning,
        timestamp=datetime.utcnow(),
    )
    db.add(log)