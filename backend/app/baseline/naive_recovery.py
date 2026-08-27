"""
Naive baseline recovery — no diagnosis, no segmentation, no guardrails.
Used ONLY for comparison against RAAHI's intelligent pipeline. Runs against
a separate, identical copy of the synthetic dataset so the comparison is fair
(same starting conditions, same real Razorpay API, same webhook confirmation).
"""
from datetime import datetime
from sqlalchemy.orm import Session
import time
from app.models.transaction import Transaction
from app.models.audit_log import AuditLog
from app.services.razorpay_client import create_payment_link, create_invoice

NAIVE_MAX_ATTEMPTS = 3


def run_naive_recovery(db: Session, transactions: list[Transaction]) -> dict:
    """
    Applies the SAME action to every record, regardless of root cause,
    amount, segment, or timing. No cost-awareness, no cooldown, no DND,
    no escalation logic — the way most merchants operate without an
    intelligent recovery agent.
    """
    link_created_count = 0
    skipped_count = 0

    for txn in transactions:
        if txn.attempts_made >= NAIVE_MAX_ATTEMPTS:
            skipped_count += 1
            continue

        customer = txn.customer
        try:
            if txn.record_type == "invoice":
                result = create_invoice(
                    amount=txn.amount,
                    customer_name=customer.name if customer else "Customer",
                    customer_email=customer.email if customer else "test@example.com",
                    customer_phone=customer.phone if customer else "9999999999",
                    description=f"Payment reminder — {txn.id}",
                )
            else:
                result = create_payment_link(
                    amount=txn.amount,
                    customer_name=customer.name if customer else "Customer",
                    customer_email=customer.email if customer else "test@example.com",
                    customer_phone=customer.phone if customer else "9999999999",
                    description=f"Payment reminder — {txn.id}",
                )

            txn.razorpay_payment_link_id = result.get("id")
            txn.payment_link_url = result.get("short_url")
            txn.attempts_made += 1
            txn.status = "recovering"
            txn.outcome_source = "naive_baseline"

            db.add(AuditLog(
                transaction_id=txn.id, stage="execution",
                summary="Naive baseline: generic reminder sent",
                reasoning="No diagnosis, no segmentation, no guardrails — same treatment for all records.",
                timestamp=datetime.utcnow(),
            ))
            link_created_count += 1

        except Exception as e:
            db.add(AuditLog(
                transaction_id=txn.id, stage="execution",
                summary=f"Naive baseline: creation failed ({str(e)[:100]})",
                reasoning="No retry logic — naive approach doesn't diagnose or adapt to failures.",
                timestamp=datetime.utcnow(),
            ))
            skipped_count += 1

        db.commit()
        time.sleep(0.3)

    return {"link_created_count": link_created_count, "skipped_count": skipped_count}