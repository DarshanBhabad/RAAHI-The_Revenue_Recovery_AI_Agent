from fastapi import APIRouter
from app.orchestrator.pipeline import run_full_pipeline
from app.orchestrator import scheduler as scheduler_module

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/run")
def trigger_pipeline_now():
    """Manually trigger one pipeline cycle immediately — useful for demos and testing."""
    result = run_full_pipeline()
    scheduler_module.latest_result = result
    return result


@router.get("/last-run")
def get_last_run():
    """See the result of the most recent pipeline run (scheduled or manual)."""
    return scheduler_module.latest_result