from datetime import datetime
from app.db.database import SessionLocal
from app.agents.detection_agent import run_detection
from app.agents.diagnosis_agent import run_diagnosis
from app.agents.decision_agent import run_decision
from app.agents.guardrail_agent import run_guardrail
from app.agents.execution_agent import run_execution
from app.agents.link_status_checker import check_pending_links
from app.agents.link_status_checker import check_pending_links, check_broken_promises

def run_full_pipeline(merchant_id: str | None = None) -> dict:
    """
    Runs the complete RAAHI pipeline once:
    Detection -> Diagnosis -> Decision -> Guardrail -> Execution
    Safe to call repeatedly (e.g. on a schedule) — each stage only
    processes records that are currently eligible.
    """
    db = SessionLocal()
    started_at = datetime.utcnow()

    try:
        poll_result = check_pending_links(db)
        promise_result = check_broken_promises(db)
        detected = run_detection(db, merchant_id=merchant_id)

        if not detected:
            return {
                "started_at": started_at.isoformat(),
                "detected_count": 0,
                "message": "No eligible at-risk records this cycle.",
            }

        diag_result = run_diagnosis(db, detected)
        decision_result = run_decision(db, detected)
        guard_result = run_guardrail(db, detected)

        approved_ids = set(guard_result["approved_ids"])
        approved_txns = [t for t in detected if t.id in approved_ids]
        exec_result = run_execution(db, approved_txns)

        return {
            "started_at": started_at.isoformat(),
            "finished_at": datetime.utcnow().isoformat(),
            "detected_count": len(detected),
            "diagnosed_count": diag_result["diagnosed_count"],
            "systemic_events": diag_result["systemic_events"],
            "needs_human_review": len(diag_result["needs_human_review"]),
            "actioned_count": decision_result["actioned_count"],
            "escalated_count": decision_result["escalated_count"],
            "guardrail_approved": guard_result["approved_count"],
            "guardrail_modified": guard_result["modified_count"],
            "guardrail_blocked": guard_result["blocked_count"],
            "recovered_count": exec_result["recovered_count"],
            "failed_attempt_count": exec_result["failed_attempt_count"],
            "skipped_count": exec_result["skipped_count"],
            "total_recovered_amount": exec_result["total_recovered_amount"],
        }

    except Exception as e:
        db.rollback()
        return {"error": str(e), "started_at": started_at.isoformat()}
    finally:
        db.close()