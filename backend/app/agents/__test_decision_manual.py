from app.db.database import SessionLocal
from app.agents.detection_agent import run_detection
from app.agents.diagnosis_agent import run_diagnosis
from app.agents.decision_agent import run_decision

db = SessionLocal()

detected = run_detection(db)
print(f"✅ Detected {len(detected)} at-risk records")

diag_result = run_diagnosis(db, detected)
print(f"✅ Diagnosed {diag_result['diagnosed_count']} records")

decision_result = run_decision(db, detected)
print(f"✅ Actioned {decision_result['actioned_count']} records")
print(f"   Escalated to human/exception: {decision_result['escalated_count']}")

db.close()