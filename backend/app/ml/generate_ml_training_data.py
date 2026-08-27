"""
Generates a large synthetic dataset purely for ML confidence-model training.
Bypasses Execution entirely (no real Razorpay API calls, no voice generation)
since training only needs root_cause + features + a labeled outcome —
completely decoupled from the production pipeline's real-world side effects.
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


def generate_ml_training_dataset(num_records_per_merchant: int = 500):
    # 1. Generate a large synthetic batch (fast, local, no external calls)
    generate_synthetic_batch(num_records_per_merchant=num_records_per_merchant, merchant_suffix="_mltrain")

    db = SessionLocal()
    try:
        # 2. Run Detection + Diagnosis only — NOT Execution (skips Razorpay/voice entirely)
        detected = [
            t for t in run_detection(db)
            if t.merchant_id.endswith("_mltrain")
        ]
        print(f"Detected {len(detected)} records for ML training set")

        run_diagnosis(db, detected)  # cached, cheap — real root causes assigned

        # 3. Directly assign labeled outcomes using the adjusted probability model
        #    (skips real link creation entirely — this is training data, not production activity)
        recovered_count = 0
        for txn in detected:
            probability = get_adjusted_probability(txn)
            if random.random() < probability:
                txn.status = "recovered"
                txn.recovered_amount = txn.amount
            else:
                txn.status = "recovering"
            txn.outcome_source = "training_simulation"
            recovered_count += 1 if txn.status == "recovered" else 0

        db.commit()
        print(f"✅ ML training dataset ready: {len(detected)} records, {recovered_count} labeled recovered.")

    finally:
        db.close()


if __name__ == "__main__":
    generate_ml_training_dataset(num_records_per_merchant=500)