from datetime import datetime
from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.models.audit_log import AuditLog
from app.policies.guardrail_rules import (
    is_within_dnd_window,
    cooldown_satisfied,
    attempts_within_limit,
    next_allowed_time,
)

NON_COMMS_ACTIONS = {"auto_retry", "no_action_exhausted", "escalate_human_review", "no_contact_opted_out"}

# Above this many attempts, fully automated action stops entirely — human review required,
# regardless of what Decision picked. A hard ceiling on autonomous escalation.
ESCALATION_CEILING = 3

# High-value customers get a gentler cap on repeated automated contact —
# protects the relationship rather than treating every customer identically.
RELATIONSHIP_GUARD_ATTEMPT_THRESHOLD = 1


def _is_method_down(root_cause: str) -> bool:
    """Checks Razorpay's real-time downtime signal for the relevant payment method."""
    method_map = {"bank_side_issue": "netbanking", "network_issue": "card"}
    method = method_map.get(root_cause)
    if not method:
        return False
    from app.services.cache_service import _get_client
    client = _get_client()
    try:
        if client:
            return client.get(f"downtime:{method}") is not None
    except Exception:
        pass
    return False


def run_guardrail(db: Session, transactions: list[Transaction]) -> dict:
    """
    Final deterministic safety gate before execution.
    Verdict per record: 'approved', 'modified', or 'blocked'.
    No LLM involved — pure rule checks, fully auditable, each tagged with a
    machine-readable violation code for structured reporting.
    """
    approved, modified, blocked = [], [], []
    now = datetime.utcnow()

    for txn in transactions:

        # Already routed to internal queue by Decision agent -> nothing to gate, pass through
        if txn.channel == "internal_queue" or txn.decided_action in (
            "no_action_exhausted", "escalate_human_review", "no_contact_opted_out"
        ):
            _log(db, txn, "approved", "APPROVED_PRE_ROUTED",
                 "Already routed to internal queue by Decision agent — no comms action to gate.")
            approved.append(txn.id)
            continue

        # Check 0: active promise-to-pay — explicit, auditable suppression
        # (previously only implicit via next_eligible_at excluding the record from Detection)
        if txn.promised_pay_date and not txn.promise_broken and txn.promised_pay_date > now:
            confidence_text = f"{txn.promise_confidence:.0%}" if txn.promise_confidence is not None else "unknown"
            _log(db, txn, "modified", "PROMISE_ACTIVE",
                 f"Active promise-to-pay logged for {txn.promised_pay_date.date()} "
                 f"(confidence: {confidence_text}). Contact suspended until then.")
            modified.append(txn.id)
            continue

        # Check 1: attempt limit
        if not attempts_within_limit(txn.attempts_made, txn.max_attempts):
            txn.decided_action = "no_action_exhausted"
            txn.channel = "internal_queue"
            txn.is_exception = True
            txn.exception_reason = "Blocked by guardrail: attempt limit reached"
            _log(db, txn, "blocked", "ATTEMPT_LIMIT_EXCEEDED",
                 f"Attempt limit reached ({txn.attempts_made}/{txn.max_attempts}). "
                 f"Action blocked, routed to exception queue.")
            blocked.append(txn.id)
            continue

        # Check 2: escalation ceiling — hard stop on automation, independent of max_attempts,
        # forces human sign-off once a record has been through this many automated cycles
        if txn.attempts_made >= ESCALATION_CEILING:
            txn.decided_action = "escalate_human_review"
            txn.channel = "internal_queue"
            txn.is_exception = True
            txn.exception_reason = "Escalation ceiling reached — requires human review"
            _log(db, txn, "blocked", "ESCALATION_CEILING",
                 f"Attempt {txn.attempts_made} reaches the escalation ceiling ({ESCALATION_CEILING}). "
                 f"Automated action stopped; requires human sign-off before any further contact.")
            blocked.append(txn.id)
            continue

        # Check 3: relationship guard — high-value customers get a gentler automated cap
        if (txn.customer and txn.customer.ltv_segment == "high"
                and txn.attempts_made > RELATIONSHIP_GUARD_ATTEMPT_THRESHOLD
                and txn.channel not in ("voice", "internal_queue")):
            original_channel = txn.channel
            txn.channel = "voice"
            _log(db, txn, "modified", "RELATIONSHIP_GUARD",
                 f"High-value customer with {txn.attempts_made} prior attempts — downgraded from "
                 f"'{original_channel}' to a more personal 'voice' touch to protect the relationship.")
            modified.append(txn.id)
            continue

        # Check 4: cooldown since last attempt — only applies if an attempt was already made
        if txn.attempts_made > 0 and not cooldown_satisfied(txn.updated_at, now):
            _log(db, txn, "modified", "COOLDOWN_ACTIVE",
                 f"Cooldown not yet satisfied since last attempt at {txn.updated_at}. "
                 f"Action deferred, not executed this cycle.")
            modified.append(txn.id)
            continue

        # Check 5: ML-recommended retry timing window not yet reached
        if txn.next_eligible_at and txn.next_eligible_at > now:
            _log(db, txn, "modified", "RETRY_TIMING_WINDOW",
                 f"ML-recommended retry window not yet reached. Eligible again at "
                 f"{txn.next_eligible_at.isoformat()}.")
            modified.append(txn.id)
            continue

        # Check 6: Razorpay-confirmed payment method downtime — real-time signal, not inferred
        if _is_method_down(txn.root_cause):
            _log(db, txn, "modified", "DOWNTIME_ACTIVE",
                 "Deferred: Razorpay reports active downtime for this payment method. "
                 "Will retry once resolved.")
            modified.append(txn.id)
            continue

        # Check 7: DND window — only applies to customer-contact actions
        involves_contact = txn.decided_action not in NON_COMMS_ACTIONS
        if involves_contact and is_within_dnd_window(now):
            next_time = next_allowed_time(now)
            txn.next_eligible_at = next_time
            _log(db, txn, "modified", "DND_WINDOW",
                 f"Action deferred: current time falls within DND window (9 PM-9 AM IST). "
                 f"Next eligible attempt at {next_time.isoformat()}.")
            modified.append(txn.id)
            continue

        # All checks passed
        _log(db, txn, "approved", "APPROVED_ALL_CHECKS_PASSED",
             f"All guardrail checks passed: attempts {txn.attempts_made}/{txn.max_attempts}, "
             f"below escalation ceiling, no relationship guard trigger, cooldown satisfied, "
             f"no active downtime, outside DND window, no active promise. Cleared for execution.")
        approved.append(txn.id)

    db.commit()

    return {
        "approved_count": len(approved),
        "modified_count": len(modified),
        "blocked_count": len(blocked),
        "approved_ids": approved,
    }


def _log(db: Session, txn: Transaction, verdict: str, violation_code: str, reasoning: str):
    log = AuditLog(
        transaction_id=txn.id,
        stage="guardrail",
        summary=f"Guardrail verdict: {verdict} [{violation_code}]",
        reasoning=reasoning,
        violation_code=violation_code,
        timestamp=datetime.utcnow(),
    )
    db.add(log)