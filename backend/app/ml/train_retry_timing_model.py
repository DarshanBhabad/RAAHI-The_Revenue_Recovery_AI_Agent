import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.metrics import roc_auc_score

from app.ml.generate_retry_timing_data import generate_retry_attempts
from app.policies.retry_timing_ground_truth import HOUR_BUCKETS, TRUE_BEST_BUCKET

MODEL_PATH = "app/ml/model_artifacts/retry_timing_model.joblib"
LOOKUP_PATH = "app/ml/model_artifacts/retry_timing_recommendations.json"


def train():
    df = generate_retry_attempts(n_per_cause=300)
    df["cause_bucket"] = df["root_cause"] + "__" + df["hour_bucket"]  # explicit interaction feature
    print(f"📊 Generated {len(df)} synthetic retry-attempt records.")

    X = df[["cause_bucket", "is_weekend"]]
    y = df["success"]

    preprocessor = ColumnTransformer(transformers=[
        ("cat", OneHotEncoder(handle_unknown="ignore"), ["cause_bucket"]),
    ], remainder="passthrough")

    pipeline = Pipeline([("preprocess", preprocessor), ("classifier", LogisticRegression(max_iter=1000))])

    cv_scores = cross_val_score(pipeline, X, y, cv=5, scoring="roc_auc")
    print(f"📈 5-fold CV ROC-AUC: {cv_scores.mean():.3f} (+/- {cv_scores.std():.3f})")

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
    pipeline.fit(X_train, y_train)
    held_out_auc = roc_auc_score(y_test, pipeline.predict_proba(X_test)[:, 1])
    print(f"✅ Held-out ROC-AUC: {held_out_auc:.3f}")

    recommendations = {}
    baseline_vs_recommended = {}

    for cause in TRUE_BEST_BUCKET.keys():
        best_bucket, best_prob = None, -1
        baseline_prob = None

        for bucket in HOUR_BUCKETS.keys():
            row = pd.DataFrame([{"cause_bucket": f"{cause}__{bucket}", "is_weekend": 0}])
            prob = pipeline.predict_proba(row)[0][1]
            if bucket == "afternoon":
                baseline_prob = prob
            if prob > best_prob:
                best_prob, best_bucket = prob, bucket

        recommendations[cause] = {"recommended_bucket": best_bucket, "predicted_success_rate": round(best_prob, 3)}
        baseline_vs_recommended[cause] = {
            "baseline_success_rate": round(baseline_prob, 3),
            "recommended_success_rate": round(best_prob, 3),
            "improvement_pct": round((best_prob - baseline_prob) / baseline_prob * 100, 1) if baseline_prob > 0 else 0,
        }

    joblib.dump(pipeline, MODEL_PATH)

    import json
    with open(LOOKUP_PATH, "w") as f:
        json.dump({
            "recommendations": recommendations,
            "comparison_vs_baseline": baseline_vs_recommended,
            "cv_roc_auc": round(cv_scores.mean(), 3),
        }, f, indent=2)

    print("\n=== Recommended retry timing per root cause ===")
    for cause, rec in recommendations.items():
        comp = baseline_vs_recommended[cause]
        print(f"  {cause:28s} -> {rec['recommended_bucket']:10s} "
              f"({comp['improvement_pct']:+.1f}% vs baseline)")

    print(f"\n💾 Model and recommendations saved.")
    return pipeline

if __name__ == "__main__":
    train()