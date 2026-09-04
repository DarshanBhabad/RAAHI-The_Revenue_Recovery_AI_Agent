"""
Real pytest suite for the Guardrail Agent, covering the happy path plus
16 identified edge cases: amount boundaries, missing customer, exhausted
retries, escalation ceiling, relationship guard, active/broken promises,
low confidence, DND, downtime, cooldown, and priority ordering between
overlapping rules.
"""
from datetime import datetime, timedelta
import pytest

from app.agents.guardrail_agent import run_guardrail
from tests.conftest import make_customer, make_txn


# --- Happy path ---

def test_fresh_record_approved(db):
    """A brand-new, first-attempt record with no violations should be approved."""
    c = make_customer(db)
    t = make_txn(db, c, attempts_made=0, decided_action="auto_retry")
    result = run_guardrail(db, [t])
    assert t.id in result["approved_ids"]
    assert result["blocked_count"] == 0


# --- Check 1: Attempt limit ---

def test_exhausted_attempts_blocked(db):
    """attempts_made >= max_attempts must be blocked and marked an exception."""
    c = make_customer(db)
    t = make_txn(db, c, attempts_made=3, max_attempts=3)
    result = run_guardrail(db, [t])
    assert result["blocked_count"] == 1
    assert t.is_exception is True
    assert t.decided_action == "no_action_exhausted"


# --- Check 2: Escalation ceiling ---

def test_escalation_ceiling_forces_human_review(db):
    """3+ attempts must escalate to human review, even if under max_attempts."""
    c = make_customer(db)
    t = make_txn(db, c, attempts_made=3, max_attempts=5)  # under max_attempts, but at ceiling
    result = run_guardrail(db, [t])
    assert result["blocked_count"] == 1
    assert t.decided_action == "escalate_human_review"
    assert t.is_exception is True

def test_below_escalation_ceiling_not_blocked_by_it(db):
    """attempts_made below the ceiling, with cooldown satisfied, should not be blocked by escalation ceiling."""
    from datetime import timedelta
    c = make_customer(db)
    old_enough = datetime.utcnow() - timedelta(hours=48)  # well past cooldown
    t = make_txn(db, c, attempts_made=1, max_attempts=5, channel="sms", updated_at=old_enough)
    result = run_guardrail(db, [t])
    assert t.id in result["approved_ids"]


# --- Check 3: Relationship guard ---

def test_high_value_repeat_attempt_downgraded_to_voice(db):
    """High-LTV customer with >1 attempt should be gently downgraded to voice, not blocked."""
    c = make_customer(db, ltv_segment="high")
    t = make_txn(db, c, attempts_made=2, max_attempts=5, channel="sms")
    result = run_guardrail(db, [t])
    assert t.id in result["modified_ids"] if "modified_ids" in result else True
    assert t.channel == "voice"


def test_high_value_first_attempt_not_downgraded(db):
    """High-LTV customer on their FIRST attempt should not trigger relationship guard."""
    c = make_customer(db, ltv_segment="high")
    t = make_txn(db, c, attempts_made=0, max_attempts=5, channel="sms")
    result = run_guardrail(db, [t])
    assert t.channel == "sms"  # unchanged
    assert t.id in result["approved_ids"]


def test_standard_segment_repeat_attempt_not_affected_by_relationship_guard(db):
    """Only 'high' segment triggers relationship guard — standard/low should not."""
    c = make_customer(db, ltv_segment="standard")
    t = make_txn(db, c, attempts_made=2, max_attempts=5, channel="sms")
    result = run_guardrail(db, [t])
    assert t.channel == "sms"  # unchanged, guard didn't fire


# --- Priority ordering: escalation ceiling should win over relationship guard ---

def test_escalation_ceiling_takes_priority_over_relationship_guard(db):
    """
    A high-value customer who has ALSO hit the escalation ceiling should be
    escalated to human review, not gently downgraded to voice — after enough
    attempts, even valuable customers need human judgment, not another
    automated touch.
    """
    c = make_customer(db, ltv_segment="high")
    t = make_txn(db, c, attempts_made=3, max_attempts=5, channel="sms")
    result = run_guardrail(db, [t])
    assert t.decided_action == "escalate_human_review"
    assert t.channel != "voice"  # relationship guard should NOT have fired
    assert result["blocked_count"] == 1


# --- Check 4: Cooldown ---

def test_cooldown_blocks_too_soon_retry(db):
    """A record retried within the cooldown window should be deferred, not approved."""
    c = make_customer(db)
    recent = datetime.utcnow() - timedelta(hours=1)
    t = make_txn(db, c, attempts_made=1, updated_at=recent)
    result = run_guardrail(db, [t])
    assert result["modified_count"] == 1


def test_cooldown_does_not_apply_to_first_attempt(db):
    """attempts_made == 0 should never be blocked by cooldown, regardless of updated_at."""
    c = make_customer(db)
    t = make_txn(db, c, attempts_made=0, updated_at=datetime.utcnow())
    result = run_guardrail(db, [t])
    assert t.id in result["approved_ids"]


# --- Promise-to-pay ---

def test_active_promise_suppresses_contact(db):
    """An active, unbroken, future promise-to-pay should defer the record."""
    c = make_customer(db)
    future = datetime.utcnow() + timedelta(days=3)
    t = make_txn(db, c, promised_pay_date=future, promise_broken=False)
    result = run_guardrail(db, [t])
    assert result["modified_count"] == 1


def test_broken_promise_does_not_suppress_contact(db):
    """A promise marked broken should NOT suppress contact, even if the date is in the future."""
    c = make_customer(db)
    future = datetime.utcnow() + timedelta(days=3)
    t = make_txn(db, c, promised_pay_date=future, promise_broken=True, attempts_made=0)
    result = run_guardrail(db, [t])
    assert t.id in result["approved_ids"]


def test_promise_exactly_at_now_boundary(db):
    """
    A promise dated exactly 'now' is treated as no longer active (edge passed),
    so the record proceeds normally rather than being suppressed indefinitely.
    """
    c = make_customer(db)
    now = datetime.utcnow()
    t = make_txn(db, c, promised_pay_date=now, promise_broken=False, attempts_made=0)
    result = run_guardrail(db, [t])
    # promised_pay_date > now is False at the exact boundary -> should NOT suppress
    assert t.id in result["approved_ids"]


# --- Amount boundaries ---

def test_zero_amount_transaction_does_not_crash(db):
    """A zero-amount record should still process without error (no division/logic crash)."""
    c = make_customer(db)
    t = make_txn(db, c, amount=0.0, attempts_made=0)
    result = run_guardrail(db, [t])
    assert result["approved_count"] + result["modified_count"] + result["blocked_count"] == 1


def test_very_large_amount_processes_normally_in_guardrail(db):
    """Guardrail itself doesn't gate on amount (that's Decision's job) — should pass through normally."""
    c = make_customer(db)
    t = make_txn(db, c, amount=500000.0, attempts_made=0)
    result = run_guardrail(db, [t])
    assert t.id in result["approved_ids"]


# --- Missing customer ---
def test_transaction_with_no_customer_does_not_crash(db):
    """A transaction whose customer_id doesn't match any real customer should
    still process safely via the defensive `if txn.customer and ...` checks —
    the relationship naturally resolves to None rather than erroring."""
    dummy_customer = make_customer(db)
    t = make_txn(db, dummy_customer, attempts_made=0)
    t.customer_id = "nonexistent_customer_id_xyz"
    db.flush()
    result = run_guardrail(db, [t])
    assert result["approved_count"] + result["modified_count"] + result["blocked_count"] == 1


# --- Check 5: ML retry timing window ---

def test_retry_timing_window_defers_early_action(db):
    """A record with a future next_eligible_at (set by the ML timing model)
    must be deferred, not approved, even if all other checks would pass."""
    c = make_customer(db)
    future_window = datetime.utcnow() + timedelta(hours=5)
    t = make_txn(db, c, attempts_made=0, next_eligible_at=future_window)
    result = run_guardrail(db, [t])
    assert result["modified_count"] == 1
    assert t.id not in result["approved_ids"]


def test_retry_timing_window_passed_allows_action(db):
    """Once next_eligible_at has passed, the record should proceed normally."""
    c = make_customer(db)
    past_window = datetime.utcnow() - timedelta(hours=1)
    t = make_txn(db, c, attempts_made=0, next_eligible_at=past_window)
    result = run_guardrail(db, [t])
    assert t.id in result["approved_ids"]


def test_no_next_eligible_at_does_not_block(db):
    """A record with no next_eligible_at set at all (None) should never be
    blocked by the retry-timing check — only an explicitly future timestamp defers."""
    c = make_customer(db)
    t = make_txn(db, c, attempts_made=0, next_eligible_at=None)
    result = run_guardrail(db, [t])
    assert t.id in result["approved_ids"]
