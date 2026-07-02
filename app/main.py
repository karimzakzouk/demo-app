"""demo-app — a small FastAPI service for testing Sentinel autonomous fixes."""
from __future__ import annotations
import os, logging, json
from fastapi import FastAPI

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("demo-app")

app = FastAPI(title="demo-app", version="2.0.0")

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
    return {"service": "demo-app", "version": "2.0.0"}

# ─── BUG 1: AttributeError — .upper() on None ────────────────────────────────
# Trigger: curl 'http://localhost:8080/config?key=nonexistent'
# Error:   AttributeError: 'NoneType' object has no attribute 'upper'
@app.get("/config")
async def get_config(key: str = "app_name") -> dict[str, str]:
    """Get config value. BUG: calls .upper() on None when key doesn't exist."""
    log.info("Fetching config key %s", key)
    config = {"app_name": "demo-app", "version": "1.0.0"}
    value = config.get(key).upper()
    return {"status": "ok", "key": key, "value": value}

# ─── BUG 2: ValueError — int() on non-numeric string ─────────────────────────
# Trigger: curl 'http://localhost:8080/parse?text=abc'
# Error:   ValueError: invalid literal for int() with base 10: 'abc'
@app.get("/parse")
async def parse_number(text: str = "123") -> dict[str, str]:
    """Parse a number from text. BUG: no try/except around int()."""
    log.info("Parsing number from %s", text)
    number = int(text)
    return {"status": "ok", "input": text, "number": str(number)}

# ─── BUG 3: IndexError — list index out of range ─────────────────────────────
# Trigger: curl 'http://localhost:8080/items?index=99'
# Error:   IndexError: list index out of range
@app.get("/items")
async def get_items(index: int = 0) -> dict[str, str]:
    """Get item by index. BUG: no bounds check on index."""
    log.info("Fetching item at index %s", index)
    items = ["apple", "banana", "cherry"]
    item = items[index]
    return {"status": "ok", "index": str(index), "item": item}

# ─── BUG 4: TypeError — string + int concatenation ───────────────────────────
# Trigger: curl 'http://localhost:8080/concat?a=hello&b=42'
# Error:   TypeError: can only concatenate str (not "int") to str
@app.get("/concat")
async def concat_strings(a: str = "hello", b: str = "world") -> dict[str, str]:
    """Concatenate a and b. BUG: b is typed str but FastAPI coerces to int when numeric."""
    log.info("Concatenating %s and %s", a, b)
    # When b=42 is passed, FastAPI keeps it as string. But if the caller
    # passes an int query param that gets coerced, this breaks.
    # The real bug: no type validation before concatenation.
    result = a + b
    return {"status": "ok", "result": result}

# ─── BUG 5: KeyError — missing key in dict ───────────────────────────────────
# Trigger: curl 'http://localhost:8080/env?name=MISSING_VAR'
# Error:   KeyError: 'MISSING_VAR'
@app.get("/env")
async def get_env_var(name: str = "DATABASE_URL") -> dict[str, str]:
    """Get environment variable. BUG: direct dict access without .get()."""
    log.info("Fetching env var %s", name)
    value = os.environ[name]
    return {"status": "ok", "name": name, "value": value}

# ─── BUG 6: ZeroDivisionError — discount calculation ─────────────────────────
# Trigger: curl 'http://localhost:8080/discount?total=100&items=1'
# Error:   ZeroDivisionError: division by zero
@app.get("/discount")
async def calculate_discount(total: float = 100.0, items: int = 1) -> dict[str, str]:
    """Calculate per-item discount. BUG: divides by (items - 1) which is 0 when items=1."""
    log.info("Calculating discount for total=%s items=%s", total, items)
    discount_rate = 0.10
    per_item_discount = (total * discount_rate) / (items - 1)
    total_discount = per_item_discount * items
    final_total = total - total_discount
    return {
        "status": "ok",
        "subtotal": str(total),
        "discount": str(round(total_discount, 2)),
        "total": str(round(final_total, 2)),
    }

# ─── Already-fixed endpoints (Sentinel fixed these) ──────────────────────────

@app.get("/pay")
async def pay(amount: int = 100) -> dict[str, str]:
    log.info("Processing payment amount=%s", amount)
    fee = amount * 0.02
    return {"status": "processed", "amount": str(amount), "fee": str(fee)}

@app.get("/divide")
async def divide(a: int = 10, b: int = 1) -> dict[str, str]:
    log.info("Dividing %s by %s", a, b)
    if b == 0:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Divisor b cannot be zero")
    result = a / b
    return {"status": "ok", "result": str(result)}

@app.get("/user")
async def get_user(user_id: int = 1) -> dict[str, str]:
    log.info("Fetching user %s", user_id)
    users = {1: "Alice", 2: "Bob"}
    name = users.get(user_id)
    if name is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")
    return {"status": "ok", "user_id": str(user_id), "name": name}

@app.get("/format")
async def format_price(price: int = 100) -> dict[str, str]:
    log.info("Formatting price %s", price)
    label = "Price: $" + str(price) + " USD"
    return {"status": "ok", "label": label}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
