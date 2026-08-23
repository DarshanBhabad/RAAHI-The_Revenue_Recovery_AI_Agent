from apscheduler.schedulers.background import BackgroundScheduler
from app.orchestrator.pipeline import run_full_pipeline

scheduler = BackgroundScheduler(timezone="UTC")
PIPELINE_INTERVAL_MINUTES = 15  # testing — set back to 15 before final demo

latest_result = {"message": "No pipeline run yet."}


def scheduled_pipeline_job():
    global latest_result
    print("🔁 RAAHI scheduled pipeline run starting...", flush=True)
    result = run_full_pipeline()
    latest_result = result
    print(f"✅ RAAHI cycle complete: {result}", flush=True)


def start_scheduler():
    scheduled_pipeline_job()  # run once immediately on startup
    scheduler.add_job(
        scheduled_pipeline_job,
        "interval",
        minutes=PIPELINE_INTERVAL_MINUTES,
        id="raahi_pipeline_job",
        replace_existing=True,
    )
    scheduler.start()
    print(f"🚀 RAAHI scheduler started — running every {PIPELINE_INTERVAL_MINUTES} minutes.", flush=True)


def stop_scheduler():
    scheduler.shutdown(wait=False)