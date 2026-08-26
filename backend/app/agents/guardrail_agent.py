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

# Actions that don't involve customer contact (safe to run anytime, no DND check needed)
NON_COMMS_ACTIONS = {"auto_retry", "no_action_exhausted", "escalate_human_review", "no_contact_opted_out"}


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
    No LLM involved — pure rule checks, fully auditable and predictable.
    """
    approved, modified, blocked = [], [], []
    now = datetime.utcnow()

    for txn in transactions:

        # Already routed to internal queue by Decision agent -> nothing to gate, pass through
        if txn.channel == "internal_queue" or txn.decided_action in (
            "no_action_exhausted", "escalate_human_review", "no_contact_opted_out"
        ):
            _log(db, txn, "approved", "Already routed to internal queue by Decision agent — no comms action to gate.")
            approved.append(txn.id)
            continue

        # Check 1: attempt limit
        if not attempts_within_limit(txn.attempts_made, txn.max_attempts):
            txn.decided_action = "no_action_exhausted"
            txn.channel = "internal_queue"
            txn.is_exception = True
            txn.exception_reason = "Blocked by guardrail: attempt limit reached"
            _log(db, txn, "blocked", f"Attempt limit reached ({txn.attempts_made}/{txn.max_attempts}). "
                                       f"Action blocked, routed to exception queue.")
            blocked.append(txn.id)
            continue

        # Check 2: cooldown since last attempt — only applies if an attempt was already made
        if txn.attempts_made > 0 and not cooldown_satisfied(txn.updated_at, now):
            _log(db, txn, "modified", f"Cooldown not yet satisfied since last attempt at "
                                        f"{txn.updated_at}. Action deferred, not executed this cycle.")
            modified.append(txn.id)
            continue

        # Check 3: Razorpay-confirmed payment method downtime — real-time signal, not inferred
        if _is_method_down(txn.root_cause):
            _log(db, txn, "modified", "Deferred: Razorpay reports active downtime for this "
                                        "payment method. Will retry once resolved.")
            modified.append(txn.id)
            continue

        # Check 4: DND window — only applies to customer-contact actions
        involves_contact = txn.decided_action not in NON_COMMS_ACTIONS
        if involves_contact and is_within_dnd_window(now):
            next_time = next_allowed_time(now)
            txn.next_eligible_at = next_time
            _log(db, txn, "modified", f"Action deferred: current time falls within DND window "
                                      f"(9 PM-9 AM UTC). Next eligible attempt at {next_time.isoformat()}.")
            modified.append(txn.id)
            continue

        # All checks passed
        _log(db, txn, "approved", f"All guardrail checks passed: attempts "
                                    f"{txn.attempts_made}/{txn.max_attempts}, cooldown satisfied, "
                                    f"no active downtime, outside DND window. Cleared for execution.")
        approved.append(txn.id)

    db.commit()

    return {
        "approved_count": len(approved),
        "modified_count": len(modified),
        "blocked_count": len(blocked),
        "approved_ids": approved,
    }


def _log(db: Session, txn: Transaction, verdict: str, reasoning: str):
    log = AuditLog(
        transaction_id=txn.id,
        stage="guardrail",
        summary=f"Guardrail verdict: {verdict}",
        reasoning=reasoning,
        timestamp=datetime.utcnow(),
    )
    db.add(log)