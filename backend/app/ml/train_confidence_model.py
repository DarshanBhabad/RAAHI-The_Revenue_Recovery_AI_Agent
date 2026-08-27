"""
Trains a logistic regression to predict recovery probability from
RAAHI's own pipeline outcomes, with explicit probability calibration —
the production-standard practice ensuring a "0.7 confidence" genuinely
means ~70% real-world accuracy, not just a relative ranking.
"""
import pandas as pd
import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, roc_auc_score, classification_report, brier_score_loss

from app.db.database import SessionLocal
from app.models import Transaction

MODEL_PATH = "app/ml/model_artifacts/confidence_model.joblib"
MIN_SAMPLES_REQUIRED = 30


def load_training_data() -> pd.DataFrame:
    db = SessionLocal()
    try:
        txns = (
            db.query(Transaction)
            .filter(Transaction.status.in_(["recovered", "recovering"]))
            .filter(Transaction.root_cause.isnot(None))
            .all()
        )

        rows = []
        for t in txns:
            rows.append({
                "root_cause": t.root_cause,
                "record_type": t.record_type,
                "amount": t.amount,
                "attempts_made": t.attempts_made,
                "ltv_segment": t.customer.ltv_segment if t.customer else "standard",
                "recovered": 1 if t.status == "recovered" else 0,
            })
        return pd.DataFrame(rows)
    finally:
        db.close()


def train():
    df = load_training_data()
    print(f"📊 Loaded {len(df)} labeled samples for training.")

    if len(df) < MIN_SAMPLES_REQUIRED:
        print(f"⚠️ Only {len(df)} labeled samples available (need {MIN_SAMPLES_REQUIRED}+).")
        return None

    X = df[["root_cause", "record_type", "amount", "attempts_made", "ltv_segment"]]
    y = df["recovered"]
    print(f"   Class balance: recovered={y.sum()}, not_recovered={len(y) - y.sum()}")

    preprocessor = ColumnTransformer(transformers=[
        ("cat", OneHotEncoder(handle_unknown="ignore"), ["root_cause", "record_type", "ltv_segment"]),
    ], remainder="passthrough")

    # Base model wrapped in calibration — production-standard practice so
    # confidence scores are genuine probabilities, not just rankings.
    base_classifier = LogisticRegression(max_iter=1000)
    calibrated_classifier = CalibratedClassifierCV(base_classifier, method="sigmoid", cv=5)

    pipeline = Pipeline(steps=[
        ("preprocess", preprocessor),
        ("classifier", calibrated_classifier),
    ])

    if len(df) >= 50 and y.nunique() > 1:
        cv_scores = cross_val_score(pipeline, X, y, cv=5, scoring="roc_auc")
        print(f"\n📈 5-fold Cross-Validation ROC-AUC: {cv_scores.mean():.3f} (+/- {cv_scores.std():.3f})")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y if y.nunique() > 1 else None
    )

    pipeline.fit(X_train, y_train)

    preds = pipeline.predict(X_test)
    probs = pipeline.predict_proba(X_test)[:, 1]

    print(f"\n✅ Final calibrated model trained.")
    print(f"   Training samples: {len(X_train)} | Test samples: {len(X_test)}")
    print(f"   Held-out Accuracy: {accuracy_score(y_test, preds):.2%}")
    if y_test.nunique() > 1:
        print(f"   Held-out ROC-AUC: {roc_auc_score(y_test, probs):.3f}")
        print(f"   Brier Score (calibration quality, lower=better): {brier_score_loss(y_test, probs):.4f}")
    print("\n" + classification_report(y_test, preds, target_names=["not_recovered", "recovered"]))

    joblib.dump(pipeline, MODEL_PATH)
    print(f"💾 Calibrated model saved to {MODEL_PATH}")

    return pipeline


if __name__ == "__main__":
    train()