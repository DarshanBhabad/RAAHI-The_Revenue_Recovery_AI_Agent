# Documented Razorpay test cards mapped to our root causes.
# Source: Razorpay's official test-card-details documentation.

CARD_MAP = {
    "insufficient_funds":  {"number": "4100280000060008", "target": "Failure"},  # insufficient_fund
    "bank_side_issue":     {"number": "4100280000090000", "target": "Failure"},  # payment_timed_out
    "network_issue":       {"number": "4100280000090000", "target": "Failure"},  # payment_timed_out
    "otp_3ds_failure":     {"number": "4100280000000009", "target": "Failure"},  # authentication_failed
    "issuer_decline":      {"number": "4100280000020007", "target": "Failure"},  # gateway_technical_error
    "card_expired":        {"number": "4111111111111111", "target": "Failure"}, # generic decline (no dedicated card documented)
    "mandate_inactive":    {"number": "4111111111111111", "target": "Failure"},
    "success_card":        {"number": "4111111111111111", "target": "Success"},
}