from app.db.database import SessionLocal
from app.agents.detection_agent import run_detection
from app.agents.diagnosis_agent import run_diagnosis

db = SessionLocal()

detected = run_detection(db)
print(f"✅ Detected {len(detected)} at-risk records")

result = run_diagnosis(db, detected)
print(f"✅ Diagnosed {result['diagnosed_count']} records")
print(f"   Needs human review: {len(result['needs_human_review'])}")
print(f"   Systemic events flagged: {result['systemic_events']}")

db.close()