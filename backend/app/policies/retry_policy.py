# Maps raw failure reason codes -> normalized root-cause categories.
# This is the deterministic backbone the Diagnosis Agent relies on.

ROOT_CAUSE_MAP = {
    "insufficient_funds": "insufficient_funds",
    "issuer_unavailable": "bank_side_issue",
    "authentication_failed": "otp_3ds_failure",
    "card_declined": "issuer_decline",
    "card_expired": "card_expired",
    "network_timeout": "network_issue",
    "mandate_not_active": "mandate_inactive",
    "overdue_7d": "receivable_overdue_early",
    "overdue_15d": "receivable_overdue_mid",
    "overdue_30d": "receivable_overdue_late",
}

# Base confidence for rule-based mapping alone (before LLM adjustment)
RULE_BASED_CONFIDENCE = {
    "insufficient_funds": 0.85,
    "bank_side_issue": 0.75,
    "otp_3ds_failure": 0.80,
    "issuer_decline": 0.70,
    "card_expired": 0.90,
    "network_issue": 0.65,
    "mandate_inactive": 0.85,
    "receivable_overdue_early": 0.90,
    "receivable_overdue_mid": 0.90,
    "receivable_overdue_late": 0.90,
}


def map_root_cause(failure_reason_code: str) -> str:
    return ROOT_CAUSE_MAP.get(failure_reason_code, "unknown")


def base_confidence(root_cause: str) -> float:
    return RULE_BASED_CONFIDENCE.get(root_cause, 0.4)

# Root cause -> (action, default_channel, retry_delay_hours)
INTERVENTION_MAP = {
    "insufficient_funds":        ("retry_delayed", "auto_retry", 60),
    "bank_side_issue":           ("retry_delayed", "auto_retry", 24),
    "otp_3ds_failure":           ("send_payment_link", "whatsapp", 0),
    "issuer_decline":            ("send_payment_link", "whatsapp", 0),
    "card_expired":              ("request_card_update", "email", 0),
    "network_issue":             ("retry_immediate", "auto_retry", 1),
    "mandate_inactive":          ("mandate_retry_sequence", "sms", 24),
    "receivable_overdue_early":  ("gentle_reminder", "email", 0),
    "receivable_overdue_mid":    ("firm_reminder", "whatsapp", 0),
    "receivable_overdue_late":   ("escalation_reminder", "whatsapp", 0),
    "unknown":                   ("escalate_human_review", "internal_queue", 0),
}


def get_intervention(root_cause: str) -> tuple[str, str, int]:
    return INTERVENTION_MAP.get(root_cause, INTERVENTION_MAP["unknown"])


def adjust_channel_for_segment(base_channel: str, ltv_segment: str, action: str) -> str:
    """
    High-value customers get gentler/more personal treatment on sensitive actions.
    Low-value customers stick to cheapest automated channel.
    """
    if action in ("firm_reminder", "escalation_reminder") and ltv_segment == "high":
        return "voice_call"   # more personal touch for valuable customers
    if ltv_segment == "low" and base_channel == "whatsapp":
        return "sms"          # cheaper channel for low-value segment
    return base_channel