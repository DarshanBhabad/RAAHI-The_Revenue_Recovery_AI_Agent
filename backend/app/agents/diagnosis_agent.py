from datetime import datetime, timedelta
from collections import Counter
from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.models.audit_log import AuditLog
from app.policies.retry_policy import map_root_cause, base_confidence
from app.services.llm_service import get_diagnosis_narrative

SYSTEMIC_EVENT_THRESHOLD = 0.35  # if >35% of a batch shares one root cause, flag as systemic
LOW_CONFIDENCE_THRESHOLD = 0.5   # below this, route to human review


def run_diagnosis(db: Session, transactions: list[Transaction]) -> dict:
    """
    Diagnoses root cause + confidence for each transaction.
    Also detects systemic events across the batch (e.g. issuer-wide outage).
    Returns a summary dict including which records need human review.
    """
    needs_human_review = []
    systemic_flags = _detect_systemic_patterns(transactions)

    for txn in transactions:
        root_cause = map_root_cause(txn.failure_reason_code)
        rule_confidence = base_confidence(root_cause)

        llm_result = get_diagnosis_narrative(txn.record_type, txn.failure_reason_code, txn.amount)

        # Blend rule-based confidence with LLM confidence (weighted average)
        final_confidence = round((rule_confidence * 0.6) + (llm_result["confidence"] * 0.4), 2)

        txn.root_cause = root_cause
        txn.diagnosis_confidence = final_confidence

        is_systemic = root_cause in systemic_flags

        reasoning_parts = [llm_result["narrative"]]
        if is_systemic:
            reasoning_parts.append(
                f"⚠️ Systemic pattern detected: {systemic_flags[root_cause]['pct']:.0%} of this batch "
                f"shares root cause '{root_cause}' — likely a bank/issuer-side event, not isolated customer issues."
            )

        if final_confidence < LOW_CONFIDENCE_THRESHOLD:
            needs_human_review.append(txn.id)
            reasoning_parts.append("⚠️ Low confidence — routed for human review before any action is taken.")

        log = AuditLog(
            transaction_id=txn.id,
            stage="diagnosis",
            summary=f"Root cause: {root_cause} (confidence {final_confidence:.0%})",
            reasoning=" ".join(reasoning_parts),
            timestamp=datetime.utcnow(),
        )
        db.add(log)

    db.commit()

    return {
        "diagnosed_count": len(transactions),
        "systemic_events": systemic_flags,
        "needs_human_review": needs_human_review,
    }


def _detect_systemic_patterns(transactions: list[Transaction]) -> dict:
    """
    If a large share of the batch shares the same root cause,
    flag it as a systemic (likely bank/issuer-side) event.
    """
    total = len(transactions)
    if total == 0:
        return {}

    cause_counts = Counter(map_root_cause(t.failure_reason_code) for t in transactions)
    systemic = {}

    for cause, count in cause_counts.items():
        pct = count / total
        if pct >= SYSTEMIC_EVENT_THRESHOLD and cause not in ("receivable_overdue_early",
                                                               "receivable_overdue_mid",
                                                               "receivable_overdue_late"):
            systemic[cause] = {"count": count, "pct": pct}

    return systemic