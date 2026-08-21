# Modeled recovery-rate probabilities per root cause.
# These represent plausible real-world recovery rates for each failure category,
# used to simulate the outcome of an intervention since live customer checkout
# completion can't be forced within a backend batch run.

ROOT_CAUSE_RECOVERY_PROBABILITY = {
    "insufficient_funds": 0.55,
    "bank_side_issue": 0.65,
    "otp_3ds_failure": 0.60,
    "issuer_decline": 0.35,
    "card_expired": 0.45,
    "network_issue": 0.75,
    "mandate_inactive": 0.50,
    "receivable_overdue_early": 0.70,
    "receivable_overdue_mid": 0.50,
    "receivable_overdue_late": 0.35,
    "unknown": 0.30,
}


def get_recovery_probability(root_cause: str) -> float:
    return ROOT_CAUSE_RECOVERY_PROBABILITY.get(root_cause, 0.3)