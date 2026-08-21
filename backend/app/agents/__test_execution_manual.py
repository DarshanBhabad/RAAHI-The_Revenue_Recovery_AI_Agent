from app.db.database import SessionLocal
from app.agents.detection_agent import run_detection
from app.agents.diagnosis_agent import run_diagnosis
from app.agents.decision_agent import run_decision
from app.agents.guardrail_agent import run_guardrail
from app.agents.execution_agent import run_execution

db = SessionLocal()

detected = run_detection(db)
print(f"✅ Detected {len(detected)}")

run_diagnosis(db, detected)
print("✅ Diagnosed")

run_decision(db, detected)
print("✅ Decided")

guard_result = run_guardrail(db, detected)
print(f"✅ Guardrail: approved={guard_result['approved_count']}, "
      f"modified={guard_result['modified_count']}, blocked={guard_result['blocked_count']}")

approved_ids = set(guard_result["approved_ids"])
approved_txns = [t for t in detected if t.id in approved_ids]

exec_result = run_execution(db, approved_txns)
print(f"✅ Execution: recovered={exec_result['recovered_count']}, "
      f"failed_attempts={exec_result['failed_attempt_count']}, "
      f"skipped={exec_result['skipped_count']}")
print(f"   💰 Total recovered: ₹{exec_result['total_recovered_amount']:,.2f}")

db.close()