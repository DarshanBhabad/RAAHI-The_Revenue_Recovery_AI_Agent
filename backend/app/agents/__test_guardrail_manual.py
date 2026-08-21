from app.db.database import SessionLocal
from app.agents.detection_agent import run_detection
from app.agents.diagnosis_agent import run_diagnosis
from app.agents.decision_agent import run_decision
from app.agents.guardrail_agent import run_guardrail

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

db.close()