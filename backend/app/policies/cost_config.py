# Approximate per-action costs (INR) — used for net-recovery optimization.
# These are illustrative estimates for demo purposes, not live billing data.

CHANNEL_COST = {
    "auto_retry": 2.0,        # gateway retry cost (negligible but non-zero)
    "sms": 0.20,
    "whatsapp": 0.80,
    "email": 0.05,
    "voice_call": 3.50,
    "internal_queue": 0.0,    # human review, no direct comms cost
}

# Minimum expected recovery value to justify a paid channel.
# Below this, prefer free/cheap channels only (protects margin on tiny amounts).
LOW_VALUE_THRESHOLD = 100.0

# Above this amount, always escalate to human review regardless of confidence.
HIGH_VALUE_ESCALATION_THRESHOLD = 100000.0