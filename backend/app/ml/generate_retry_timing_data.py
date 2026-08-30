"""
Generates synthetic RETRY ATTEMPT records (not full transactions) — each with
a root_cause, a randomly-assigned attempt hour, and a genuine success label
drawn from a probability curve peaking at the assumed best-response hour bucket
for that cause. This creates a learnable pattern (not pure noise) so the
timing model can demonstrate real signal detection, same approach validated
for the confidence model.
"""
import random
import pandas as pd
from app.policies.retry_timing_ground_truth import TRUE_BEST_BUCKET, get_hour_bucket

ROOT_CAUSES = list(TRUE_BEST_BUCKET.keys())


def generate_retry_attempts(n_per_cause: int = 300) -> pd.DataFrame:
    rows = []
    for cause in ROOT_CAUSES:
        best_bucket = TRUE_BEST_BUCKET[cause]
        for _ in range(n_per_cause):
            hour = random.randint(0, 23)
            day_of_week = random.randint(0, 6)
            bucket = get_hour_bucket(hour)

            base_success = 0.35
            bump = 0.30 if bucket == best_bucket else 0.0
            weekend_bump = 0.05 if day_of_week >= 5 and "receivable" not in cause else 0.0
            noise = random.uniform(-0.05, 0.05)

            probability = min(0.9, max(0.05, base_success + bump + weekend_bump + noise))
            success = 1 if random.random() < probability else 0

            rows.append({
                "root_cause": cause,
                "hour_bucket": bucket,
                "is_weekend": 1 if day_of_week >= 5 else 0,
                "success": success,
            })

    return pd.DataFrame(rows)