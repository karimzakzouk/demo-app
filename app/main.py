"""demo-app — a small FastAPI service for testing Sentinel autonomous fixes."""
from __future__ import annotations
import os, logging, json
from fastapi import FastAPI

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("demo-app")

app = FastAPI(title="demo-app", version="3.0.0")

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
    return {"service": "demo-app", "version": "3.0.0"}

# ─── Already-fixed endpoints (Sentinel fixed these in prior runs) ────────────

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

# ─── BUG 1: AttributeError ───────────────────────────────────────────────────
# Trigger: curl 'http://localhost:8080/config?key=nonexistent'
@app.get("/config")
async def get_config(key: str = "app_name") -> dict[str, str]:
    log.info("Fetching config key %s", key)
    config = {"app_name": "demo-app", "version": "1.0.0"}
    value = config.get(key).upper()
    return {"status": "ok", "key": key, "value": value}

# ─── BUG 2: ValueError ───────────────────────────────────────────────────────
# Trigger: curl 'http://localhost:8080/parse?text=abc'
@app.get("/parse")
async def parse_number(text: str = "123") -> dict[str, str]:
    log.info("Parsing number from %s", text)
    number = int(text)
    return {"status": "ok", "input": text, "number": str(number)}

# ─── BUG 3: IndexError ───────────────────────────────────────────────────────
# Trigger: curl 'http://localhost:8080/items?index=99'
@app.get("/items")
async def get_items(index: int = 0) -> dict[str, str]:
    log.info("Fetching item at index %s", index)
    items = ["apple", "banana", "cherry"]
    item = items[index]
    return {"status": "ok", "index": str(index), "item": item}

# ─── BUG 4: TypeError ────────────────────────────────────────────────────────
# Trigger: curl 'http://localhost:8080/concat?a=hello&b=42'
@app.get("/concat")
async def concat_strings(a: str = "hello", b: int = 42) -> dict[str, str]:
    log.info("Concatenating %s and %s", a, b)
    result = a + b
    return {"status": "ok", "result": result}

# ─── BUG 5: KeyError ─────────────────────────────────────────────────────────
# Trigger: curl 'http://localhost:8080/env?name=MISSING_VAR'
@app.get("/env")
async def get_env_var(name: str = "DATABASE_URL") -> dict[str, str]:
    log.info("Fetching env var %s", name)
    value = os.environ.get(name)
    if value is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Environment variable not found")
    return {"status": "ok", "name": name, "value": value}

# ─── BUG 6: ZeroDivisionError ────────────────────────────────────────────────
# Trigger: curl 'http://localhost:8080/discount?total=100&items=1'
@app.get("/discount")
async def calculate_discount(total: float = 100.0, items: int = 1) -> dict[str, str]:
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

# ═══════════════════════════════════════════════════════════════════════════
# COMPLEX BUG 7: Multi-step shopping cart with nested discount + tax logic
# ═══════════════════════════════════════════════════════════════════════════
#
# This is a REAL business-logic bug, not a simple missing-check.
# The code has THREE interacting pieces that all have to be correct:
#
# 1. Coupon validation — coupons have type (percentage/fixed) and value.
#    A percentage coupon divides the discount by 100 to get the rate.
#    BUG: the percentage is used directly (e.g. "20" means 20% but code
#    treats it as 2000% because it doesn't divide by 100).
#
# 2. Tax calculation — tax is applied AFTER discount.
#    tax_amount = (subtotal - discount) * tax_rate
#    BUG: tax is calculated on the FULL subtotal, not the discounted total.
#    The code does: tax_amount = subtotal * tax_rate
#    Should be:   tax_amount = (subtotal - discount) * tax_rate
#
# 3. Free shipping threshold — orders over $100 get free shipping.
#    The threshold check compares the PRE-discount subtotal.
#    BUG: the code compares the POST-discount total, so a $105 order with
#    a $10 coupon ($95 after discount) incorrectly charges shipping.
#
# The crash happens because of bug #1: when a percentage coupon value
# like "20" is used, the discount becomes subtotal * 20 = $2000 on a $100
# order. The final total goes negative, and then the free-shipping check
# compares a negative number, and the response includes a negative total
# which is logically wrong (not a crash, but a critical business bug).
#
# BUT — the actual CRASH is a different path: when a coupon code "BOGO"
# is passed, the code tries to look it up in the coupons dict, doesn't
# find it, gets None, then tries to access .get("type") on None →
# AttributeError: 'NoneType' object has no attribute 'get'
#
# Trigger: curl 'http://localhost:8080/cart?items=widget:2,gadget:1&coupon=BOGO'
# Error:   AttributeError: 'NoneType' object has no attribute 'get'

# Simulated product catalog
PRODUCTS = {
    "widget": {"price": 25.00, "category": "electronics"},
    "gadget": {"price": 15.00, "category": "electronics"},
    "doohickey": {"price": 5.00, "category": "misc"},
    "thingamajig": {"price": 50.00, "category": "premium"},
}

# Simulated coupon codes
COUPONS = {
    "SAVE10": {"type": "percentage", "value": 10},
    "SAVE20": {"type": "percentage", "value": 20},
    "FLAT5": {"type": "fixed", "value": 5.00},
}

@app.get("/cart")
async def calculate_cart(
    items: str = "widget:1",
    coupon: str = "",
    tax_rate: float = 0.08,
) -> dict[str, str]:
    """Calculate shopping cart total with coupon discount + tax + shipping.

    BUGS (3 interacting):
    1. Coupon lookup returns None for unknown codes → .get() on None crashes
    2. Percentage coupon doesn't divide by 100 (20% becomes 2000%)
    3. Tax calculated on pre-discount subtotal instead of post-discount
    4. Free shipping threshold checks post-discount total instead of pre-discount

    Trigger: curl 'http://localhost:8080/cart?items=widget:2,gadget:1&coupon=BOGO'
    """
    log.info("Calculating cart: items=%s coupon=%s tax_rate=%s", items, coupon, tax_rate)

    # Parse items: "widget:2,gadget:1" → [("widget", 2), ("gadget", 1)]
    parsed_items = []
    for item_str in items.split(","):
        name, qty_str = item_str.split(":")
        parsed_items.append((name.strip(), int(qty_str)))

    # Calculate subtotal
    subtotal = 0.0
    for name, qty in parsed_items:
        product = PRODUCTS.get(name)
        if product is None:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail=f"Product '{name}' not found")
        subtotal += product["price"] * qty

    # Apply coupon discount
    discount = 0.0
    if coupon:
        coupon_data = COUPONS.get(coupon)  # BUG 1: returns None for unknown coupon
        coupon_type = coupon_data.get("type")  # CRASH: NoneType.get() → AttributeError
        coupon_value = coupon_data.get("value")

        if coupon_type == "percentage":
            # BUG 2: should be coupon_value / 100, not coupon_value directly
            discount = subtotal * coupon_value
        elif coupon_type == "fixed":
            discount = coupon_value

    # Calculate tax
    # BUG 3: tax should be on (subtotal - discount), not subtotal
    tax_amount = subtotal * tax_rate

    # Determine shipping
    # BUG 4: should check subtotal (pre-discount), not (subtotal - discount)
    # Free shipping for orders over $100
    if (subtotal - discount) > 100:
        shipping = 0.0
    else:
        shipping = 9.99

    total = subtotal - discount + tax_amount + shipping

    return {
        "status": "ok",
        "subtotal": f"${round(subtotal, 2)}",
        "discount": f"${round(discount, 2)}",
        "tax": f"${round(tax_amount, 2)}",
        "shipping": f"${round(shipping, 2)}",
        "total": f"${round(total, 2)}",
        "items_count": str(len(parsed_items)),
    }

# ─── COMPLEX BUG 8: Race condition in counter (deterministic crash) ──────────
# This is NOT a simple missing check — it's a logic bug where the code
# accumulates a running balance across calls but doesn't initialize properly.
#
# The code simulates a bank account with deposits and withdrawals.
# The bug: withdraw() doesn't check if the balance is sufficient before
# withdrawing. When balance goes negative, a subsequent call to
# get_balance() tries to format the negative balance as a percentage
# (for the "interest" field) by doing: balance / 100 * rate
# If balance is 0 (after a withdrawal that emptied the account), this
# is fine. But if balance went NEGATIVE (overdraft), the interest
# calculation does negative / 100 which is fine mathematically BUT —
# the real crash is that get_balance() calls log.info with a format
# string that expects a float but gets a string (because withdraw()
# stored the balance as a string, not a float, when it went negative).
#
# Actually, the REAL crash is simpler: the /account/withdraw endpoint
# accesses account["balance"] without checking if the account exists.
# An unknown account_id → KeyError.
#
# Trigger: curl 'http://localhost:8080/account/withdraw?account_id=UNKNOWN&amount=50'
# Error:   KeyError: 'UNKNOWN'

# Simulated bank accounts
ACCOUNTS = {
    "ACC-001": {"balance": 1000.00, "owner": "Alice", "type": "checking"},
    "ACC-002": {"balance": 500.00, "owner": "Bob", "type": "savings"},
}

@app.get("/account/balance")
async def get_account_balance(account_id: str = "ACC-001") -> dict[str, str]:
    """Get account balance with interest calculation."""
    log.info("Fetching balance for account %s", account_id)
    account = ACCOUNTS[account_id]  # BUG: KeyError on unknown account_id
    balance = account["balance"]
    interest = balance * 0.05  # 5% annual interest
    return {
        "status": "ok",
        "account_id": account_id,
        "owner": account["owner"],
        "balance": f"${round(balance, 2)}",
        "interest": f"${round(interest, 2)}",
    }

@app.get("/account/withdraw")
async def withdraw(account_id: str = "ACC-001", amount: float = 0) -> dict[str, str]:
    """Withdraw from account. BUG: no account existence check + no balance check."""
    log.info("Withdrawing %s from account %s", amount, account_id)
    account = ACCOUNTS[account_id]  # BUG: KeyError on unknown account_id
    account["balance"] -= amount  # BUG: no overdraft check — balance can go negative
    return {
        "status": "ok",
        "account_id": account_id,
        "new_balance": f"${round(account['balance'], 2)}",
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
