"""
Documented assumptions about when customers are most responsive, by failure
category — used to generate a learnable synthetic pattern for the retry-timing
model. These reflect plausible real-world behavior (e.g., personal card issues
resolved in the evening after work; B2B invoices handled during business hours)
but are modeling assumptions, not measured production data. In production,
RAAHI would learn these directly from real outcome timestamps instead.
"""

HOUR_BUCKETS = {
    "night": (0, 5),
    "morning": (6, 11),
    "afternoon": (12, 16),
    "evening": (17, 21),
    "late_night": (22, 23),
}

# Assumed best-response bucket per root cause
TRUE_BEST_BUCKET = {
    "insufficient_funds": "evening",       # checks banking app after work
    "bank_side_issue": "morning",          # bank systems freshest early
    "otp_3ds_failure": "evening",
    "issuer_decline": "evening",
    "card_expired": "afternoon",
    "network_timeout": "afternoon",
    "mandate_inactive": "morning",
    "receivable_overdue_early": "afternoon",  # B2B — business hours
    "receivable_overdue_mid": "afternoon",
    "receivable_overdue_late": "morning",     # first thing, before day gets busy
    "checkout_abandoned": "evening",
    "unknown": "afternoon",
}


def get_hour_bucket(hour: int) -> str:
    for bucket, (start, end) in HOUR_BUCKETS.items():
        if start <= hour <= end:
            return bucket
    return "afternoon"


def bucket_to_next_hour(bucket: str, now_hour: int) -> int:
    """Returns hours-from-now until the start of the target bucket."""
    start_hour = HOUR_BUCKETS[bucket][0]
    if start_hour >= now_hour:
        return start_hour - now_hour
    return (24 - now_hour) + start_hour