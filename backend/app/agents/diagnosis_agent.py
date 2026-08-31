from datetime import datetime
from collections import Counter
import os
import joblib
import pandas as pd
from sqlalchemy.orm import Session

from app.ml.confidence_model import predict_ml_confidence
from app.models.transaction import Transaction
from app.models.audit_log import AuditLog
from app.policies.retry_policy import map_root_cause, base_confidence
from app.services.llm_service import get_diagnosis_narrative

SYSTEMIC_EVENT_THRESHOLD = 0.35
LOW_CONFIDENCE_THRESHOLD = 0.5

META_MODEL_PATH = "app/ml/model_artifacts/meta_blend_model.joblib"
_meta_model = None
_meta_model_loaded = False


def _load_meta_model():
    global _meta_model, _meta_model_loaded
    if _meta_model_loaded:
        return _meta_model
    _meta_model_loaded = True
    if os.path.exists(META_MODEL_PATH):
        _meta_model = joblib.load(META_MODEL_PATH)
        print("✅ Meta-blend model loaded.", flush=True)
    else:
        print("⚠️ No meta-blend model found — falling back to fixed-weight blend.", flush=True)
        _meta_model = None
    return _meta_model


def run_diagnosis(db: Session, transactions: list[Transaction]) -> dict:
    """
    Diagnoses root cause + confidence for each transaction.
    Also detects systemic events across the batch (e.g. issuer-wide outage).
    Returns a summary dict including which records need human review.
    """
    needs_human_review = []
    systemic_flags = _detect_systemic_patterns(transactions)
    meta_model = _load_meta_model()

    for txn in transactions:
        root_cause = map_root_cause(txn.failure_reason_code)
        rule_confidence = base_confidence(root_cause)

        llm_result = get_diagnosis_narrative(txn.record_type, txn.failure_reason_code, txn.amount)

        segment = txn.customer.ltv_segment if txn.customer else "standard"
        ml_confidence = predict_ml_confidence(
            root_cause, txn.record_type, txn.amount, txn.attempts_made, segment
        )

        if ml_confidence is not None and meta_model is not None:
            # Learned meta-blend available: use it to combine all three signals
            # (validated at 0.655 CV-ROC-AUC vs. 0.626 for the fixed-weight blend)
            meta_input = pd.DataFrame([{
                "ml_confidence_raw": ml_confidence,
                "rule_confidence_raw": rule_confidence,
                "llm_confidence_raw": llm_result["confidence"],
            }])
            final_confidence = round(float(meta_model.predict_proba(meta_input)[0][1]), 2)
            confidence_source = "meta_blend_model"
        elif ml_confidence is not None:
            # Meta-blend unavailable but ML model is: fall back to fixed-weight blend
            final_confidence = round((ml_confidence * 0.5) + (rule_confidence * 0.3) + (llm_result["confidence"] * 0.2), 2)
            confidence_source = "ml_model_fixed_blend"
        else:
            # No trained ML model yet: fall back to rule + LLM blend only
            final_confidence = round((rule_confidence * 0.6) + (llm_result["confidence"] * 0.4), 2)
            confidence_source = "rule_based_fallback"

        # Log each raw signal separately — enables genuine meta-blend retraining later
        # on freshly logged, non-approximated data.
        txn.rule_confidence_raw = rule_confidence
        txn.llm_confidence_raw = llm_result["confidence"]
        txn.ml_confidence_raw = ml_confidence if ml_confidence is not None else None

        txn.root_cause = root_cause
        txn.diagnosis_confidence = final_confidence

        is_systemic = root_cause in systemic_flags

        reasoning_parts = [llm_result["narrative"], f"[confidence source: {confidence_source}]"]
        if is_systemic:
            reasoning_parts.append(
                f"⚠️ Systemic pattern detected: {systemic_flags[root_cause]['pct']:.0%} of this batch "
                f"shares root cause '{root_cause}' — likely a bank/issuer-side event, not isolated customer issues."
            )

        if final_confidence < LOW_CONFIDENCE_THRESHOLD:
            needs_human_review.append(txn.id)
            reasoning_parts.append("⚠️ Low confidence — routed for human review before any action is taken.")

        log = AuditLog(
            transaction_id=txn.id,
            stage="diagnosis",
            summary=f"Root cause: {root_cause} (confidence {final_confidence:.0%})",
            reasoning=" ".join(reasoning_parts),
            timestamp=datetime.utcnow(),
        )
        db.add(log)

    db.commit()

    return {
        "diagnosed_count": len(transactions),
        "systemic_events": systemic_flags,
        "needs_human_review": needs_human_review,
    }


def _detect_systemic_patterns(transactions: list[Transaction]) -> dict:
    total = len(transactions)
    if total == 0:
        return {}

    cause_counts = Counter(map_root_cause(t.failure_reason_code) for t in transactions)
    systemic = {}

    for cause, count in cause_counts.items():
        pct = count / total
        if pct >= SYSTEMIC_EVENT_THRESHOLD and cause not in ("receivable_overdue_early",
                                                               "receivable_overdue_mid",
                                                               "receivable_overdue_late"):
            systemic[cause] = {"count": count, "pct": pct}

    return systemic