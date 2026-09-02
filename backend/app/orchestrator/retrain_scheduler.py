"""
Periodically retrains models that genuinely benefit from fresh data —
the confidence model and meta-blend, both trained against the live
transactions table. Scheduled for weekend nights (low-traffic window),
since retraining more frequently wouldn't reflect meaningfully new data
without sustained real production traffic. The retry-timing model is
excluded: it trains on static synthetic ground truth, not accumulating
real data, so scheduled retraining wouldn't add value there.
"""
import os
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

RETRAIN_ENABLED = os.getenv("RAAHI_RETRAIN_SCHEDULER_ENABLED", "true").lower() == "true"

scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
last_retrain_result = {"message": "No scheduled retrain has run yet."}


def retrain_job():
    global last_retrain_result
    print(f"🔁 Scheduled model retraining starting at {datetime.utcnow().isoformat()}...", flush=True)

    result = {"timestamp": datetime.utcnow().isoformat(), "confidence_model": None, "meta_blend": None}

    try:
        from app.ml.train_confidence_model import train as train_confidence
        train_confidence()
        result["confidence_model"] = "success"
    except Exception as e:
        result["confidence_model"] = f"failed: {str(e)[:150]}"
        print(f"⚠️ Confidence model retrain failed: {str(e)[:150]}", flush=True)

    try:
        from app.ml.train_meta_blend import train_meta_blend
        train_meta_blend()
        result["meta_blend"] = "success"
    except Exception as e:
        result["meta_blend"] = f"failed: {str(e)[:150]}"
        print(f"⚠️ Meta-blend retrain failed: {str(e)[:150]}", flush=True)

    last_retrain_result = result
    print(f"✅ Scheduled retraining complete: {result}", flush=True)


def start_retrain_scheduler():
    if not RETRAIN_ENABLED:
        print("⏸️ Retrain scheduler disabled via RAAHI_RETRAIN_SCHEDULER_ENABLED=false.", flush=True)
        return

    # Run once shortly after startup, just to prove the mechanism works immediately
    scheduler.add_job(
        retrain_job,
        "date",
        run_date=datetime.utcnow() + timedelta(seconds=10),
        id="raahi_initial_retrain",
    )

    # Then on a real schedule: Saturday and Sunday nights at 11 PM IST —
    # a realistic low-traffic maintenance window for a merchant-facing system.
    scheduler.add_job(
        retrain_job,
        CronTrigger(day_of_week="sat,sun", hour=23, minute=0),
        id="raahi_weekend_retrain",
        replace_existing=True,
    )
    scheduler.start()
    print("🚀 Model retrain scheduler started — weekends at 11 PM IST.", flush=True)


def stop_retrain_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)