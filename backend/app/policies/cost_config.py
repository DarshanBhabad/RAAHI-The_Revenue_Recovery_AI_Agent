# Approximate per-action costs (INR) — used for net-recovery optimization.

CHANNEL_COST = {
    "auto_retry":      2.0,   # gateway retry cost
    "sms":             0.20,  # Razorpay native SMS notification
    "email":           0.05,  # Razorpay native email notification
    "internal_queue":  0.0,   # human review, no direct send cost
}

# Below this amount, prefer SMS over email (marginal cost difference, but consistent).
LOW_VALUE_THRESHOLD = 100.0

# Above this amount, always escalate to human review regardless of confidence.
HIGH_VALUE_ESCALATION_THRESHOLD = 100000.0