"""
Runs Detection + Diagnosis ONLY (no Execution, no Razorpay calls, no voice
generation) on a fresh synthetic batch, purely to populate genuinely separate
ml_confidence_raw / rule_confidence_raw / llm_confidence_raw signals for
meta-blend training. Outcomes are then labeled using the same calibrated
probability model used for the main ML training dataset.
"""
import random
from app.db.database import SessionLocal
from app.agents.detection_agent import run_detection
from app.agents.diagnosis_agent import run_diagnosis
from app.policies.recovery_probability import get_recovery_probability
from data_generator.generate_synthetic_data import generate as generate_synthetic_batch


def get_adjusted_probability(txn) -> float:
    base = get_recovery_probability(txn.root_cause)
    if txn.amount > 20000:
        base *= 0.7
    if txn.attempts_made >= 2:
        base *= 0.8
    if txn.customer and txn.customer.ltv_segment == "high":
        base *= 1.15
    return min(0.95, max(0.05, base))


def collect_meta_blend_data(num_records_per_merchant: int = 300):
    generate_synthetic_batch(num_records_per_merchant=num_records_per_merchant, merchant_suffix="_metablend")

    db = SessionLocal()
    try:
        detected = [
            t for t in run_detection(db)
            if t.merchant_id.endswith("_metablend")
        ]
        print(f"Detected {len(detected)} records for meta-blend data collection", flush=True)

        run_diagnosis(db, detected)
        print(f"✅ Diagnosis complete — ml_confidence_raw, rule_confidence_raw, "
              f"llm_confidence_raw now populated for all {len(detected)} records", flush=True)

        total = len(detected)
        recovered_count = 0
        for i, txn in enumerate(detected, 1):
            probability = get_adjusted_probability(txn)
            if random.random() < probability:
                txn.status = "recovered"
                txn.recovered_amount = txn.amount
                recovered_count += 1
            else:
                txn.status = "recovering"
            txn.outcome_source = "training_simulation"

            db.commit()  # per-record commit — crash resilience

            if i % 100 == 0 or i == total:
                print(f"⏳ Labeling: {i}/{total} (recovered so far: {recovered_count})", flush=True)

        print(f"✅ Meta-blend dataset ready: {total} records, {recovered_count} labeled recovered "
              f"({recovered_count/total*100:.1f}%).", flush=True)

    finally:
        db.close()


if __name__ == "__main__":
    collect_meta_blend_data(num_records_per_merchant=300)