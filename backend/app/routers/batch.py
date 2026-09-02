from fastapi import APIRouter
from app.orchestrator.pipeline import run_full_pipeline

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

latest_result = {"message": "No pipeline run yet."}


@router.post("/run")
def trigger_pipeline_now():
    """Manually trigger one pipeline cycle immediately — useful for demos and testing."""
    global latest_result
    latest_result = run_full_pipeline()
    return latest_result


@router.get("/last-run")
def get_last_run():
    """See the result of the most recent pipeline run (manual only)."""
    return latest_result