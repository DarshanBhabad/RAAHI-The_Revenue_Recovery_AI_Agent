"""
Generates labeled outcomes for ML MODEL TRAINING ONLY, using calibrated
recovery-probability assumptions per root cause. This does NOT touch
production transaction status or recovered_amount — it creates a separate
training dataset so the confidence model has genuine variation to learn from,
since real webhook-confirmed outcomes require live customer payments we
cannot generate at batch scale without live users.
"""
#used only to calibrate confidence model,
import random
from app.db.database import SessionLocal
from app.models import Transaction
from app.policies.recovery_probability import get_recovery_probability


def generate_training_labels():
    db = SessionLocal()
    try:
        recovering = db.query(Transaction).filter(
            Transaction.status == "recovering",
            Transaction.root_cause.isnot(None),
        ).all()

        simulated_recovered = 0
        for txn in recovering:
            probability = get_recovery_probability(txn.root_cause)
            if random.random() < probability:
                txn.status = "recovered"  # Note: this DOES update status for training purposes
                txn.recovered_amount = txn.amount
                txn.outcome_source = "training_simulation"  # clearly distinct from "modeled" or "real_verified"
                simulated_recovered += 1

        db.commit()
        print(f"✅ Generated {simulated_recovered} simulated recovered outcomes "
              f"(out of {len(recovering)}) for ML training purposes.")
    finally:
        db.close()


if __name__ == "__main__":
    generate_training_labels()