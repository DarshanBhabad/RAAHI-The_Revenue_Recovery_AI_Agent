from datetime import datetime
from sqlalchemy.orm import Session
import time  # add this import at the top of the file
from app.models.transaction import Transaction
from app.models.audit_log import AuditLog
from app.services.razorpay_client import create_payment_link, create_invoice, create_plan, create_subscription
from app.services.voice_service import generate_hinglish_script, generate_voice_audio

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
            _generate_voice_message_if_applicable(db, txn)
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
    customer_name = customer.name if customer else "Customer"
    customer_email = customer.email if customer else "test@example.com"
    customer_phone = customer.phone if customer else "9999999999"

    try:
        if txn.record_type == "invoice":
            result = create_invoice(
                amount=txn.amount,
                customer_name=customer_name,
                customer_email=customer_email,
                customer_phone=customer_phone,
                description=f"RAAHI recovery — overdue invoice {txn.id}",
            )
            txn.razorpay_payment_link_id = result.get("id")
            txn.payment_link_url = result.get("short_url")
            instrument_type = "invoice"

        elif txn.record_type == "subscription":
            plan = create_plan(amount=txn.amount, plan_name=f"RAAHI Recovery Plan — {txn.id}")
            sub = create_subscription(plan_id=plan["id"])
            txn.razorpay_payment_link_id = sub.get("id")
            txn.payment_link_url = sub.get("short_url")
            instrument_type = "subscription"

        else:  # "payment"
            result = create_payment_link(
                amount=txn.amount,
                customer_name=customer_name,
                customer_email=customer_email,
                customer_phone=customer_phone,
                description=f"RAAHI recovery — {txn.record_type} {txn.id}",
            )
            txn.razorpay_payment_link_id = result.get("id")
            txn.payment_link_url = result.get("short_url")
            instrument_type = "payment_link"

        txn.attempts_made += 1
        txn.status = "recovering"
        _log(db, txn, f"✅ Real Razorpay {instrument_type} created: {txn.payment_link_url}. "
                        f"Attempt {txn.attempts_made}/{txn.max_attempts}.")

    except Exception as e:
        _log(db, txn, f"❌ Recovery instrument creation failed ({txn.record_type}): {str(e)[:150]}")
    time.sleep(0.3)  # ← pacing: avoid hitting Razorpay's rate limits during large batches    

def _generate_voice_message_if_applicable(db: Session, txn: Transaction):
    """
    Generates a REAL Hinglish voice script (via LLM) and a REAL playable
    Hindi audio file (via gTTS) — this is genuine generated audio, not a mockup.
    """
    voice_worthy_actions = {"firm_reminder", "escalation_reminder", "gentle_reminder"}
    if txn.decided_action not in voice_worthy_actions:
        return

    customer = txn.customer
    try:
        script = generate_hinglish_script(
            customer_name=customer.name if customer else "Customer",
            amount=txn.amount,
            days_overdue=txn.attempts_made,
        )
        audio_url = generate_voice_audio(script)

        txn.voice_message_text = script
        txn.voice_message_url = audio_url

        _log(db, txn, f"🔊 Real Hinglish voice message generated (playable audio): \"{script}\"")

    except Exception as e:
        _log(db, txn, f"⚠️ Voice message generation failed: {str(e)[:100]}")

def _log(db: Session, txn: Transaction, reasoning: str):
    log = AuditLog(
        transaction_id=txn.id,
        stage="execution",
        summary=f"Execution: {txn.decided_action} → {txn.status}",
        reasoning=reasoning,
        timestamp=datetime.utcnow(),
    )
    db.add(log)