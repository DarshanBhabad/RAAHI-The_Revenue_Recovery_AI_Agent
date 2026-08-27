"""
Learns the optimal weighting between ML confidence, rule-based confidence,
and LLM confidence — replacing hand-picked weights (0.5/0.3/0.2) with
weights learned from RAAHI's own outcome data. This is a small, second-stage
model trained on the OUTPUT of the three existing signals, not raw features.
"""
import pandas as pd
import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
from sklearn.metrics import roc_auc_score

from app.db.database import SessionLocal
from app.models import Transaction
from app.policies.retry_policy import map_root_cause, base_confidence

META_MODEL_PATH = "app/ml/model_artifacts/meta_blend_model.joblib"


def build_meta_training_data() -> pd.DataFrame:
    """
    Reconstructs what each signal (rule, ML placeholder, LLM placeholder) would
    have said for each historical record, paired with the real outcome.
    Note: this uses rule_confidence directly from the policy table; for a full
    production version, RAAHI would log each signal's raw score at diagnosis
    time rather than reconstructing it after the fact.
    """
    db = SessionLocal()
    try:
        txns = (
            db.query(Transaction)
            .filter(Transaction.status.in_(["recovered", "recovering"]))
            .filter(Transaction.root_cause.isnot(None))
            .filter(Transaction.diagnosis_confidence.isnot(None))
            .all()
        )

        rows = []
        for t in txns:
            rows.append({
                "rule_confidence": base_confidence(t.root_cause),
                "blended_confidence_at_diagnosis": t.diagnosis_confidence,  # the historical blended score
                "recovered": 1 if t.status == "recovered" else 0,
            })
        return pd.DataFrame(rows)
    finally:
        db.close()


def train_meta_blend():
    df = build_meta_training_data()
    print(f"📊 Loaded {len(df)} samples for meta-blend training.")

    if len(df) < 50:
        print("⚠️ Not enough samples with diagnosis_confidence logged for meta-blend training.")
        return None

    X = df[["rule_confidence", "blended_confidence_at_diagnosis"]]
    y = df["recovered"]

    meta_model = LogisticRegression(max_iter=1000)

    cv_scores = cross_val_score(meta_model, X, y, cv=5, scoring="roc_auc")
    print(f"📈 Meta-blend 5-fold CV ROC-AUC: {cv_scores.mean():.3f} (+/- {cv_scores.std():.3f})")

    meta_model.fit(X, y)

    print(f"\n✅ Learned blend coefficients:")
    for feature, coef in zip(X.columns, meta_model.coef_[0]):
        print(f"   {feature}: {coef:.4f}")

    joblib.dump(meta_model, META_MODEL_PATH)
    print(f"💾 Meta-blend model saved to {META_MODEL_PATH}")

    return meta_model


if __name__ == "__main__":
    train_meta_blend()