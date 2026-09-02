from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.orchestrator.retrain_scheduler import start_retrain_scheduler, stop_retrain_scheduler
from app.routers import batch, records, dashboard, webhooks, checkout

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_retrain_scheduler()  # model retraining only — pipeline is manual-trigger only
    yield
    stop_retrain_scheduler()

app = FastAPI(title="RAAHI — The Revenue Recovery AI Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(batch.router)
app.include_router(records.router)
app.include_router(dashboard.router)
app.include_router(webhooks.router)
app.include_router(checkout.router)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "RAAHI"}