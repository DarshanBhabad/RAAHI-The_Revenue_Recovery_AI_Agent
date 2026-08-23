from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.orchestrator.scheduler import start_scheduler, stop_scheduler
from app.routers import batch, records, dashboard, test_checkout


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="RAAHI — The Revenue Recovery AI Agent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(batch.router)
app.include_router(records.router)
app.include_router(dashboard.router)
app.include_router(test_checkout.router)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "RAAHI"}