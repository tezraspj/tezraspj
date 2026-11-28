"""Smoke test against a running server (default http://127.0.0.1:8000)."""
import json
import sys
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"


def get(path):
    with urllib.request.urlopen(BASE + path) as r:
        return r.status, json.loads(r.read())


def post(path, payload, headers=None):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


print("health:", get("/api/health"))
print("restaurants:", len(get("/api/restaurants")[1]))
print("promo SALE10:", get("/api/promos/validate?code=SALE10")[1])
print("promo BADCODE:", get("/api/promos/validate?code=BADCODE")[1])

# Fetch a real menu item
rests = get("/api/restaurants")[1]
rest = next(r for r in rests if r["menu"])
item = rest["menu"][0]
print("using:", rest["id"], item["id"], item["price"])

status, order = post(
    "/api/orders",
    {
        "restaurant_id": rest["id"],
        "promo_code": "SALE10",
        "client": {
            "name": "Тест Клиент",
            "phone": "+992 90 111 22 33",
            "address": "Улица Рудаки, дом 1",
            "comment": "позвонить за 5 минут",
        },
        "items": [{"item_id": item["id"], "qty": 3, "price": 1.0}],  # price ignored
    },
)
print("create order:", status, json.dumps(order, ensure_ascii=False)[:300])

# cross-restaurant item must be rejected
other = next(r for r in rests if r["id"] != rest["id"] and r["menu"])
status2, body2 = post(
    "/api/orders",
    {
        "restaurant_id": rest["id"],
        "client": {"name": "Тест", "phone": "+992901112233", "address": "Улица Ленина, дом 5"},
        "items": [{"item_id": other["menu"][0]["id"], "qty": 1}],
    },
)
print("cross-restaurant:", status2, body2)

# admin without token
try:
    req = urllib.request.Request(BASE + "/api/admin/orders")
    with urllib.request.urlopen(req) as r:
        print("admin no token:", r.status)
except urllib.error.HTTPError as e:
    print("admin no token:", e.code)

# admin with token
status3, body3 = post(
    "/api/admin/promos",
    {"code": "SMOKE5", "percent": 5},
    headers={"Authorization": "Bearer dev-admin-token"},
)
print("admin create promo:", status3, body3)

print("statuses:", [s["value"] for s in get("/api/statuses")[1]])
