"""demo-app — a small FastAPI service for testing K8s deployments."""
from __future__ import annotations
import os, logging
from fastapi import FastAPI

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
    if b == 0:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Divisor b cannot be zero")
    result = a / b  # ZeroDivisionError when b=0
    return {"status": "ok", "result": str(result)}

@app.get("/user")
async def get_user(user_id: int = 1) -> dict[str, str]:
    """Get user by ID. BUG: accesses a key that doesn't exist in the users dict."""
    log.info("Fetching user %s", user_id)
    users = {1: "Alice", 2: "Bob"}
    name = users[user_id]
    return {"status": "ok", "user_id": str(user_id), "name": name}

@app.get("/format")
async def format_price(price: int = 100) -> dict[str, str]:
    """Format a price string. BUG: concatenates string with int directly."""
    log.info("Formatting price %s", price)
    label = "Price: $" + str(price) + " USD"
    return {"status": "ok", "label": label}

@app.get("/items")
async def get_items(index: int = 0) -> dict[str, str]:
    """Get item by index."""
    log.info("Fetching item at index %s", index)
    items = ["apple", "banana", "cherry"]
    if index < 0 or index >= len(items):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Index out of range")
    item = items[index]
    return {"status": "ok", "index": str(index), "item": item}

@app.get("/config")
async def get_config(key: str = "app_name") -> dict[str, str]:
    """Get config value. BUG: calls .upper() on None."""
    log.info("Fetching config key %s", key)
    config = {"app_name": "demo-app", "version": "1.0.0"}
    value = config.get(key).upper()
    return {"status": "ok", "key": key, "value": value}

@app.get("/parse")
async def parse_number(text: str = "123") -> dict[str, str]:
    """Parse a number from text. BUG: no try/except around int()."""
    log.info("Parsing number from %s", text)
    number = int(text)
    return {"status": "ok", "input": text, "number": str(number)}

# ─── NEW: Harder bug — multi-step order processing ───────────────────────────

# Simulated order database
orders = {
    "ORD-001": {"items": ["widget", "gadget"], "quantities": [2, 1], "prices": [10.0, 25.0]},
    "ORD-002": {"items": ["widget"], "quantities": [3], "prices": [10.0]},
    "ORD-003": {"items": ["gadget", "widget", "doohickey"], "quantities": [1, 1, 1], "prices": [25.0, 10.0, 5.0]},
}

@app.get("/order")
async def calculate_order_total(order_id: str = "ORD-001") -> dict[str, str]:
    """Calculate the total for an order.

    BUG: The discount logic divides by zero when an order has only one item.
    The code calculates a per-item discount rate by dividing the total discount
    by the number of items. When there's only 1 item, the discount division
    uses (len(items) - 1) as the denominator, which is 0.

    This is a logic bug — not a simple missing check. The LLM needs to:
    1. Understand the discount calculation flow
    2. Identify that (num_items - 1) can be zero
    3. Fix the discount logic so it doesn't divide by zero
    4. Keep the discount working correctly for multi-item orders

    Trigger: /order?order_id=ORD-002 (single-item order)
    """
    log.info("Calculating total for order %s", order_id)

    order = orders.get(order_id)
    if not order:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Order not found")

    items = order["items"]
    quantities = order["quantities"]
    prices = order["prices"]

    # Calculate subtotal
    subtotal = 0.0
    for i in range(len(items)):
        subtotal += quantities[i] * prices[i]

    # Apply bulk discount: orders with >1 item get 10% off
    if len(items) > 1:
    total_discount = subtotal * 0.10
    else:
    total_discount = 0.0
    total = subtotal - total_discount

    return {
        "status": "ok",
        "order_id": order_id,
        "items": str(len(items)),
        "subtotal": str(round(subtotal, 2)),
        "discount": str(round(total_discount, 2)),
        "total": str(round(total, 2)),
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
