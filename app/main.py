"""demo-app — a small FastAPI service for testing K8s deployments."""
from __future__ import annotations
import os, logging
from fastapi import FastAPI, HTTPException

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("demo-app")

app = FastAPI(title="demo-app", version="1.0.0")

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///demo.db")
API_KEY = os.environ.get("API_KEY", "default-key")

@app.on_event("startup")
async def _startup() -> None:
    log.info("demo-app starting up — DATABASE_URL=%s", DATABASE_URL)

@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/readyz")
async def readyz() -> dict[str, str]:
    return {"status": "ready", "database": DATABASE_URL}

@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "demo-app", "version": "1.0.0"}

@app.get("/pay")
async def pay(amount: int = 100) -> dict[str, str]:
    log.info("Processing payment amount=%s", amount)
    fee = amount * 0.02
    return {"status": "processed", "amount": str(amount), "fee": str(fee)}

@app.get("/divide")
async def divide(a: int = 10, b: int = 1) -> dict[str, str]:
    """Divide a by b. Returns error if b is zero."""
    log.info("Dividing %s by %s", a, b)
    if b == 0:
        raise HTTPException(status_code=400, detail="Division by zero is not allowed")
    result = a / b
    return {"status": "ok", "result": str(result)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
