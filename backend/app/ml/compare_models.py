"""
Compares Logistic Regression against LightGBM on the same training data,
using identical preprocessing and cross-validation, for an honest model
selection decision rather than defaulting to one approach.
"""
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.metrics import roc_auc_score, accuracy_score, classification_report
from lightgbm import LGBMClassifier

from app.ml.train_confidence_model import load_training_data


def compare():
    df = load_training_data()
    print(f"📊 Loaded {len(df)} labeled samples.\n")

    X = df[["root_cause", "record_type", "amount", "attempts_made", "ltv_segment"]]
    y = df["recovered"]

    preprocessor = ColumnTransformer(transformers=[
        ("cat", OneHotEncoder(handle_unknown="ignore"), ["root_cause", "record_type", "ltv_segment"]),
    ], remainder="passthrough")

    models = {
        "Logistic Regression": LogisticRegression(max_iter=1000),
        "LightGBM": LGBMClassifier(n_estimators=100, max_depth=4, random_state=42, verbose=-1),
    }

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    results = {}

    for name, clf in models.items():
        pipeline = Pipeline(steps=[("preprocess", preprocessor), ("classifier", clf)])

        cv_scores = cross_val_score(pipeline, X, y, cv=5, scoring="roc_auc")

        pipeline.fit(X_train, y_train)
        preds = pipeline.predict(X_test)
        probs = pipeline.predict_proba(X_test)[:, 1]

        held_out_auc = roc_auc_score(y_test, probs)
        held_out_acc = accuracy_score(y_test, preds)

        results[name] = {
            "cv_mean": cv_scores.mean(),
            "cv_std": cv_scores.std(),
            "held_out_auc": held_out_auc,
            "held_out_acc": held_out_acc,
        }

        print(f"=== {name} ===")
        print(f"5-fold CV ROC-AUC: {cv_scores.mean():.3f} (+/- {cv_scores.std():.3f})")
        print(f"Held-out ROC-AUC: {held_out_auc:.3f}")
        print(f"Held-out Accuracy: {held_out_acc:.2%}")
        print(classification_report(y_test, preds, target_names=["not_recovered", "recovered"]))
        print()

    print("=== Summary ===")
    for name, r in results.items():
        print(f"{name:25s} | CV-AUC: {r['cv_mean']:.3f} (+/-{r['cv_std']:.3f}) | Held-out AUC: {r['held_out_auc']:.3f}")

    return results


if __name__ == "__main__":
    compare()