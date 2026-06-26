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
    """Divide a by b. BUG: no zero check — calling /divide?a=10&b=0 crashes."""
    log.info("Dividing %s by %s", a, b)
    result = a / b  # ZeroDivisionError when b=0
    return {"status": "ok", "result": str(result)}

@app.get("/user")
async def get_user(user_id: int = 1) -> dict[str, str]:
    """Get user by ID. BUG: accesses a key that doesn't exist in the users dict."""
    log.info("Fetching user %s", user_id)
    users = {1: "Alice", 2: "Bob"}
    # BUG: KeyError when user_id is not 1 or 2 (e.g. /user?user_id=99)
    name = users[user_id]
    return {"status": "ok", "user_id": str(user_id), "name": name}

@app.get("/format")
async def format_price(price: int = 100) -> dict[str, str]:
    """Format a price string. BUG: concatenates string with int directly."""
    log.info("Formatting price %s", price)
    # BUG: TypeError — can't concatenate str and int
    # /format?price=50 crashes with "can only concatenate str (not "int") to str"
    label = "Price: $" + price + " USD"
    return {"status": "ok", "label": label}

@app.get("/items")
async def get_items(index: int = 0) -> dict[str, str]:
    """Get item by index. BUG: no bounds check on the list."""
    log.info("Fetching item at index %s", index)
    items = ["apple", "banana", "cherry"]
    if index < 0 or index >= len(items):
        raise HTTPException(status_code=404, detail=f'Index {index} out of range for list of length {len(items)}')
    item = items[index]
    return {"status": "ok", "index": str(index), "item": item}

@app.get("/config")
async def get_config(key: str = "app_name") -> dict[str, str]:
    """Get config value. BUG: calls .upper() on None."""
    log.info("Fetching config key %s", key)
    config = {"app_name": "demo-app", "version": "1.0.0"}
    # BUG: AttributeError — NoneType has no attribute 'upper'
    # /config?key=nonexistent crashes because config.get(key) returns None
    value = config.get(key).upper()
    return {"status": "ok", "key": key, "value": value}

@app.get("/parse")
async def parse_number(text: str = "123") -> dict[str, str]:
    """Parse a number from text. BUG: no try/except around int()."""
    log.info("Parsing number from %s", text)
    # BUG: ValueError — invalid literal for int() with base 10
    # /parse?text=abc crashes
    number = int(text)
    return {"status": "ok", "input": text, "number": str(number)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
