from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="RAAHI — The Revenue Recovery AI Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # tighten this before any real deployment
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "RAAHI"}