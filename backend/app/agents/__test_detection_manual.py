from app.db.database import SessionLocal
from app.agents.detection_agent import run_detection

db = SessionLocal()
results = run_detection(db)
print(f"✅ Detection agent flagged {len(results)} at-risk records")
for r in results[:5]:
    print(" -", r.id, r.record_type, r.amount, r.failure_reason_code)
db.close()