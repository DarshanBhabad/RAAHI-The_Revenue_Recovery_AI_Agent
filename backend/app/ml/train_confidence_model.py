"""
Trains a logistic regression to predict recovery probability from
RAAHI's own pipeline outcomes — no external dataset needed, since
real recovery-outcome data is proprietary to each merchant and simply
doesn't exist as a public dataset. This model retrains on RAAHI's own
accumulated results, improving as more batches run.
"""
import pandas as pd
import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score, classification_report

from app.db.database import SessionLocal
from app.models import Transaction

MODEL_PATH = "app/ml/model_artifacts/confidence_model.joblib"
MIN_SAMPLES_REQUIRED = 30  # below this, model won't be statistically meaningful


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

    if len(df) < MIN_SAMPLES_REQUIRED:
        print(f"⚠️ Only {len(df)} labeled samples available (need {MIN_SAMPLES_REQUIRED}+). "
              f"Run the pipeline (detection→diagnosis→decision→guardrail→execution) on a larger "
              f"batch first, then retrain.")
        return None

    X = df[["root_cause", "record_type", "amount", "attempts_made", "ltv_segment"]]
    y = df["recovered"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y if y.nunique() > 1 else None
    )

    preprocessor = ColumnTransformer(transformers=[
        ("cat", OneHotEncoder(handle_unknown="ignore"), ["root_cause", "record_type", "ltv_segment"]),
    ], remainder="passthrough")

    pipeline = Pipeline(steps=[
        ("preprocess", preprocessor),
        ("classifier", LogisticRegression(max_iter=1000)),
    ])

    pipeline.fit(X_train, y_train)

    preds = pipeline.predict(X_test)
    probs = pipeline.predict_proba(X_test)[:, 1]

    print("✅ Model trained.")
    print(f"   Training samples: {len(X_train)} | Test samples: {len(X_test)}")
    print(f"   Accuracy: {accuracy_score(y_test, preds):.2%}")
    if y_test.nunique() > 1:
        print(f"   ROC-AUC: {roc_auc_score(y_test, probs):.3f}")
    print("\n" + classification_report(y_test, preds, target_names=["not_recovered", "recovered"]))

    joblib.dump(pipeline, MODEL_PATH)
    print(f"💾 Model saved to {MODEL_PATH}")

    return pipeline


if __name__ == "__main__":
    train()