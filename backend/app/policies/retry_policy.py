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
    "checkout_abandoned": "checkout_abandoned",
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
    "checkout_abandoned": 0.95,
}


def map_root_cause(failure_reason_code: str) -> str:
    return ROOT_CAUSE_MAP.get(failure_reason_code, "unknown")


def base_confidence(root_cause: str) -> float:
    return RULE_BASED_CONFIDENCE.get(root_cause, 0.4)


# Root cause -> (action, channel, retry_delay_hours)
# Channels: "sms" or "email" only.
# SMS  — Razorpay sends a short payment link message to the customer's phone.
# Email — Razorpay sends a payment link email to the customer's address.
INTERVENTION_MAP = {
    "insufficient_funds":        ("retry_delayed",         "sms",    2),
    "bank_side_issue":           ("retry_delayed",         "sms",    1),
    "otp_3ds_failure":           ("send_payment_link",     "email",  0),
    "issuer_decline":            ("send_payment_link",     "email",  0),
    "card_expired":              ("request_card_update",   "email",  0),
    "network_issue":             ("retry_immediate",       "sms",    0),
    "mandate_inactive":          ("send_payment_link",     "email",  1),
    "receivable_overdue_early":  ("gentle_reminder",       "email",  0),
    "receivable_overdue_mid":    ("firm_reminder",         "sms",    0),
    "receivable_overdue_late":   ("escalation_reminder",   "email",  0),
    "unknown":                   ("escalate_human_review", "internal_queue", 0),
    "checkout_abandoned":        ("gentle_reminder",       "email",  0),
}


def get_intervention(root_cause: str) -> tuple[str, str, int]:
    return INTERVENTION_MAP.get(root_cause, INTERVENTION_MAP["unknown"])


def adjust_channel_for_segment(base_channel: str, ltv_segment: str, action: str) -> str:
    """
    Low-value customers always get SMS (cheapest channel).
    High-value customers on escalation reminders get email (more formal/personal).
    All other cases keep the policy default.
    """
    if ltv_segment == "low" and base_channel == "email":
        return "sms"
    if ltv_segment == "high" and action == "escalation_reminder":
        return "email"
    return base_channel