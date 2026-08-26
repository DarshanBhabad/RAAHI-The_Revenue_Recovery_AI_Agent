from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.routers import batch, records, dashboard, webhooks

app = FastAPI(title="RAAHI — The Revenue Recovery AI Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(batch.router)
app.include_router(records.router)
app.include_router(dashboard.router)
app.include_router(webhooks.router)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "RAAHI"}