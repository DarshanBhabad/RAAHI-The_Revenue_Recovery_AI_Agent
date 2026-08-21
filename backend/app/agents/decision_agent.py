from datetime import datetime
from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.models.audit_log import AuditLog
from app.policies.retry_policy import get_intervention, adjust_channel_for_segment
from app.policies.cost_config import (
    CHANNEL_COST,
    LOW_VALUE_THRESHOLD,
    HIGH_VALUE_ESCALATION_THRESHOLD,
)

LOW_CONFIDENCE_THRESHOLD = 0.5  # must match diagnosis_agent.py


def run_decision(db: Session, transactions: list[Transaction]) -> dict:
    """
    Decides the intervention for each transaction based on root cause,
    confidence, customer segment, and cost-aware policy.
    """
    escalated = []
    actioned = []

    for txn in transactions:

        # --- Guard: already exhausted retries -> straight to exception, no new action ---
        if txn.attempts_made >= txn.max_attempts:
            _log_decision(db, txn, "no_action_exhausted",
                          "internal_queue",
                          f"Retry attempts exhausted ({txn.attempts_made}/{txn.max_attempts}). "
                          f"No further automated action; routed to exception list.")
            txn.is_exception = True
            txn.exception_reason = "Retry attempts exhausted"
            escalated.append(txn.id)
            continue

        # --- Guard: low diagnosis confidence -> human review, no autonomous action ---
        if (txn.diagnosis_confidence or 0) < LOW_CONFIDENCE_THRESHOLD:
            _log_decision(db, txn, "escalate_human_review", "internal_queue",
                          f"Diagnosis confidence {txn.diagnosis_confidence:.0%} below threshold "
                          f"({LOW_CONFIDENCE_THRESHOLD:.0%}). Escalated to human review before any action.")
            txn.decided_action = "escalate_human_review"
            txn.channel = "internal_queue"
            escalated.append(txn.id)
            continue

        # --- Guard: opted-out customer -> no contact-based action allowed ---
        if txn.customer and txn.customer.opted_out:
            _log_decision(db, txn, "no_contact_opted_out", "internal_queue",
                          "Customer has opted out of communications. No SMS/WhatsApp/email/call "
                          "permitted. Routed to internal queue for manual/non-comms handling only.")
            txn.decided_action = "no_contact_opted_out"
            txn.channel = "internal_queue"
            escalated.append(txn.id)
            continue

        # --- Guard: very high value -> always human-escalated regardless of confidence ---
        if txn.amount >= HIGH_VALUE_ESCALATION_THRESHOLD:
            _log_decision(db, txn, "escalate_human_review", "internal_queue",
                          f"Amount ₹{txn.amount:,.2f} exceeds high-value escalation threshold "
                          f"(₹{HIGH_VALUE_ESCALATION_THRESHOLD:,.2f}). Requires human sign-off before action.")
            txn.decided_action = "escalate_human_review"
            txn.channel = "internal_queue"
            escalated.append(txn.id)
            continue

        # --- Normal path: policy-driven decision ---
        action, base_channel, delay_hours = get_intervention(txn.root_cause)
        segment = txn.customer.ltv_segment if txn.customer else "standard"
        channel = adjust_channel_for_segment(base_channel, segment, action)

        # Cost-aware check: for very low-value transactions, avoid paid channels
        cost = CHANNEL_COST.get(channel, 0.0)
        if txn.amount < LOW_VALUE_THRESHOLD and cost > CHANNEL_COST["sms"]:
            channel = "sms"
            cost = CHANNEL_COST["sms"]

        net_expected_value = txn.amount - cost

        txn.decided_action = action
        txn.channel = channel

        reasoning = (
            f"Root cause '{txn.root_cause}' (confidence {txn.diagnosis_confidence:.0%}) mapped to "
            f"action '{action}' via channel '{channel}' (segment: {segment}). "
            f"Estimated intervention cost ₹{cost:.2f} vs at-risk amount ₹{txn.amount:,.2f} "
            f"→ net expected value ₹{net_expected_value:,.2f}."
        )
        if delay_hours > 0:
            reasoning += f" Scheduled with a {delay_hours}h delay per policy."

        _log_decision(db, txn, action, channel, reasoning)
        actioned.append(txn.id)

    db.commit()

    return {
        "actioned_count": len(actioned),
        "escalated_count": len(escalated),
        "escalated_ids": escalated,
    }


def _log_decision(db: Session, txn: Transaction, action: str, channel: str, reasoning: str):
    log = AuditLog(
        transaction_id=txn.id,
        stage="decision",
        summary=f"Decision: {action} via {channel}",
        reasoning=reasoning,
        timestamp=datetime.utcnow(),
    )
    db.add(log)