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