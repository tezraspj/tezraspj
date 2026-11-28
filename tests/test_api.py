"""API integration tests (server-side pricing, validation, admin security)."""
from app.rate_limit import SlidingWindowLimiter


# ---------- System ----------
def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ---------- Restaurants / menu ----------
def test_list_restaurants(client):
    r = client.get("/api/restaurants")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 8
    assert {"id", "name", "category", "menu", "deliveryTime", "minOrder"} <= set(data[0])


def test_restaurant_detail_and_menu(client, sample_order):
    rid = sample_order["_restaurant"]["id"]
    r = client.get(f"/api/restaurants/{rid}")
    assert r.status_code == 200
    assert len(r.json()["menu"]) > 0

    r2 = client.get(f"/api/restaurants/{rid}/menu")
    assert r2.status_code == 200
    assert len(r2.json()) > 0

    assert client.get("/api/restaurants/nope").status_code == 404


# ---------- Promos ----------
def test_promo_validation(client):
    assert client.get("/api/promos/validate", params={"code": "SALE10"}).json() == {"valid": True, "percent": 10}
    assert client.get("/api/promos/validate", params={"code": "NOPE"}).json()["valid"] is False


# ---------- Orders: server-side pricing ----------
def test_order_ignores_client_price(client, sample_order):
    """Client sends price=1 — server must use the database price."""
    item = sample_order["_item"]
    payload = dict(sample_order)
    payload["items"] = [{"item_id": item["id"], "qty": 2, "price": 1.0}]
    r = client.post("/api/orders", json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["subtotal"] == item["price"] * 2
    expected_fee = 0.0 if body["subtotal"] >= 100 else 5.0
    assert body["delivery_fee"] == expected_fee
    assert body["total"] == body["subtotal"] - body["discount"] + body["delivery_fee"]


def test_free_delivery_threshold(client, sample_order):
    """Below 100 смн → fee 5; at/above 100 смн → free."""
    item = sample_order["_item"]
    # find qty to stay below threshold
    qty_below = max(1, int(99 // item["price"]))
    payload = dict(sample_order)
    payload["items"] = [{"item_id": item["id"], "qty": qty_below}]
    r1 = client.post("/api/orders", json=payload)
    assert r1.status_code == 201
    if r1.json()["subtotal"] < 100:
        assert r1.json()["delivery_fee"] == 5.0

    qty_above = int(100 // item["price"]) + 1
    payload["items"] = [{"item_id": item["id"], "qty": qty_above}]
    r2 = client.post("/api/orders", json=payload)
    assert r2.status_code == 201
    assert r2.json()["subtotal"] >= 100
    assert r2.json()["delivery_fee"] == 0.0


def test_order_with_promo(client, sample_order):
    payload = dict(sample_order)
    payload["promo_code"] = "SALE10"
    r = client.post("/api/orders", json=payload)
    assert r.status_code == 201
    body = r.json()
    assert body["discount"] == round(body["subtotal"] * 0.1, 10)
    assert body["promo_code"] == "SALE10"


def test_order_invalid_promo(client, sample_order):
    payload = dict(sample_order)
    payload["promo_code"] = "HACKED"
    assert client.post("/api/orders", json=payload).status_code == 422


# ---------- Orders: validation ----------
def test_order_invalid_phone(client, sample_order):
    payload = dict(sample_order)
    payload["client"] = dict(payload["client"], phone="12345")
    r = client.post("/api/orders", json=payload)
    assert r.status_code == 422


def test_order_invalid_name_and_short_address(client, sample_order):
    payload = dict(sample_order)
    payload["client"] = dict(payload["client"], name="1", address="abc")
    assert client.post("/api/orders", json=payload).status_code == 422


def test_order_item_from_other_restaurant_rejected(client, sample_order):
    restaurants = client.get("/api/restaurants").json()
    other = next(r for r in restaurants if r["id"] != sample_order["_restaurant"]["id"] and r["menu"])
    payload = dict(sample_order)
    payload["items"] = [{"item_id": other["menu"][0]["id"], "qty": 1}]
    assert client.post("/api/orders", json=payload).status_code == 422


def test_order_empty_items_rejected(client, sample_order):
    payload = dict(sample_order)
    payload["items"] = []
    assert client.post("/api/orders", json=payload).status_code == 422


def test_order_get_by_id(client, sample_order):
    created = client.post("/api/orders", json=sample_order).json()
    r = client.get(f"/api/orders/{created['id']}")
    assert r.status_code == 200
    assert r.json()["status"] == "new"
    assert client.get("/api/orders/99999999").status_code == 404


# ---------- Statuses ----------
def test_statuses(client):
    values = [s["value"] for s in client.get("/api/statuses").json()]
    assert values == ["new", "confirmed", "preparing", "delivering", "done", "cancelled"]


# ---------- Users ----------
def test_users(client):
    r = client.post("/api/users", json={"phone": "+992901112233", "name": "Алишер"})
    assert r.status_code == 200
    uid = r.json()["id"]
    assert client.get(f"/api/users/{uid}").json()["phone"] == "+992901112233"
    # same phone → same user
    r2 = client.post("/api/users", json={"phone": "+992901112233", "name": "Алишер"})
    assert r2.json()["id"] == uid


# ---------- Admin security ----------
def test_admin_requires_token(client):
    assert client.get("/api/admin/orders").status_code == 401
    bad = {"Authorization": "Bearer wrong"}
    assert client.get("/api/admin/orders", headers=bad).status_code == 401


def test_admin_orders_and_status_change(client, sample_order, admin_headers=None):
    headers = {"Authorization": "Bearer test-admin-token"}
    created = client.post("/api/orders", json=sample_order).json()
    r = client.get("/api/admin/orders", headers=headers)
    assert r.status_code == 200
    assert any(o["id"] == created["id"] for o in r.json())

    r2 = client.patch(f"/api/admin/orders/{created['id']}/status",
                      json={"status": "confirmed"}, headers=headers)
    assert r2.status_code == 200
    assert r2.json()["status"] == "confirmed"

    r3 = client.patch(f"/api/admin/orders/{created['id']}/status",
                      json={"status": "wrong-status"}, headers=headers)
    assert r3.status_code == 422


def test_admin_promo_crud(client):
    headers = {"Authorization": "Bearer test-admin-token"}
    r = client.post("/api/admin/promos", json={"code": "TEST20", "percent": 20}, headers=headers)
    assert r.status_code == 201
    assert client.get("/api/promos/validate", params={"code": "TEST20"}).json()["percent"] == 20

    # duplicate
    assert client.post("/api/admin/promos", json={"code": "TEST20", "percent": 20},
                       headers=headers).status_code == 409


def test_admin_menu_price_update(client):
    headers = {"Authorization": "Bearer test-admin-token"}
    menu = client.get("/api/admin/menu", headers=headers).json()
    assert menu
    item = menu[0]
    payload = {
        "id": item["id"], "restaurant_id": item["restaurant_id"], "name": item["name"],
        "category": item["category"], "price": item["price"] + 5, "image": item["image"],
        "description": item["description"], "active": True,
    }
    r = client.put(f"/api/admin/menu/{item['id']}", json=payload, headers=headers)
    assert r.status_code == 200
    check = client.get(f"/api/restaurants/{item['restaurant_id']}").json()
    updated = next(m for m in check["menu"] if m["id"] == item["id"])
    assert updated["price"] == item["price"] + 5
    # restore
    payload["price"] = item["price"]
    client.put(f"/api/admin/menu/{item['id']}", json=payload, headers=headers)


# ---------- Rate limiter (unit) ----------
def test_sliding_window_limiter():
    limiter = SlidingWindowLimiter(max_requests=3, window_seconds=60)
    now = 1000.0
    assert all(limiter.allow("ip", now + i) for i in range(3))
    assert limiter.allow("ip", now + 3) is False
    assert limiter.allow("other-ip", now + 3) is True
    # window slides
    assert limiter.allow("ip", now + 61) is True
