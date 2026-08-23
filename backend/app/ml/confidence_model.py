import os
import joblib
import pandas as pd

MODEL_PATH = "app/ml/model_artifacts/confidence_model.joblib"

_model_cache = None
_model_loaded = False


def _load_model():
    global _model_cache, _model_loaded
    if _model_loaded:
        return _model_cache
    _model_loaded = True
    if os.path.exists(MODEL_PATH):
        _model_cache = joblib.load(MODEL_PATH)
        print("✅ ML confidence model loaded.")
    else:
        print("⚠️ No trained ML confidence model found — falling back to rule-based confidence only. "
              "Run `python -m app.ml.train_confidence_model` once enough data has accumulated.")
        _model_cache = None
    return _model_cache


def predict_ml_confidence(root_cause: str, record_type: str, amount: float,
                           attempts_made: int, ltv_segment: str) -> float | None:
    """
    Returns a learned recovery-probability confidence score, or None if
    no trained model is available yet (caller should fall back to rules).
    """
    model = _load_model()
    if model is None:
        return None

    try:
        X = pd.DataFrame([{
            "root_cause": root_cause,
            "record_type": record_type,
            "amount": amount,
            "attempts_made": attempts_made,
            "ltv_segment": ltv_segment,
        }])
        proba = model.predict_proba(X)[0][1]  # probability of class "recovered"
        return float(proba)
    except Exception as e:
        print(f"⚠️ ML confidence prediction failed ({str(e)[:100]}), falling back to rule-based.")
        return None