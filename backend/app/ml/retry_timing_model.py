import json
import os
from app.policies.retry_timing_ground_truth import bucket_to_next_hour

LOOKUP_PATH = "app/ml/model_artifacts/retry_timing_recommendations.json"

_cache = None


def get_recommended_delay_hours(root_cause: str, current_hour: int) -> tuple[int, str]:
    """
    Returns (delay_hours, explanation) for when to retry, based on the
    learned timing model. Falls back to a fixed 24h delay if the model
    hasn't been trained yet.
    """
    global _cache
    if _cache is None:
        if os.path.exists(LOOKUP_PATH):
            with open(LOOKUP_PATH) as f:
                _cache = json.load(f)
        else:
            _cache = {}

    recs = _cache.get("recommendations", {})
    rec = recs.get(root_cause)

    if not rec:
        return 24, "No learned timing recommendation available — using default 24h delay."

    bucket = rec["recommended_bucket"]
    delay = bucket_to_next_hour(bucket, current_hour)
    delay = max(1, delay)  # never schedule in the past/immediately

    comparison = _cache.get("comparison_vs_baseline", {}).get(root_cause, {})
    improvement = comparison.get("improvement_pct", 0)

    explanation = (f"ML-recommended retry window: '{bucket}' — learned pattern shows "
                    f"{improvement:+.1f}% higher predicted success vs. baseline timing.")
    return delay, explanation