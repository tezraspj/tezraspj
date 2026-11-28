"""Import restaurants and menu from data/restaurants.json into the database.

Idempotent: existing restaurant/menu ids are skipped.
Usage: python seed.py  (run from the server/ directory)
"""
import json
import sys
from pathlib import Path

from app.db import SessionLocal
from app.models import Category, MenuItem, PromoCode, Restaurant

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "restaurants.json"


def seed() -> int:
    if not DATA_FILE.exists():
        print(f"Data file not found: {DATA_FILE}", file=sys.stderr)
        return 1

    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    db = SessionLocal()
    added_r = added_m = skipped = 0
    try:
        for r in data:
            if db.get(Restaurant, r["id"]):
                skipped += 1
                continue
            db.add(Restaurant(
                id=r["id"],
                name=r["name"],
                category=r["category"],
                description=r.get("description", ""),
                image=r.get("image", ""),
                rating=float(r.get("rating", 0)),
                delivery_time=r.get("deliveryTime", "20-30 мин"),
                min_order=r.get("minOrder", "0 смн"),
                active=True,
            ))
            added_r += 1
            for m in r.get("menu", []):
                db.add(MenuItem(
                    id=m["id"],
                    restaurant_id=r["id"],
                    name=m["name"],
                    category=m.get("category", ""),
                    price=float(m["price"]),
                    image=m.get("image", ""),
                    description=m.get("description", ""),
                    active=True,
                ))
                added_m += 1
            for cat in sorted({m.get("category", "") for m in r.get("menu", [])} - {""}):
                db.add(Category(restaurant_id=r["id"], name=cat))
        db.commit()
    finally:
        db.close()

    # Default promo codes (idempotent).
    db = SessionLocal()
    added_p = 0
    try:
        for code, percent in (("SALE10", 10),):
            if not db.execute(
                PromoCode.__table__.select().where(PromoCode.code == code)
            ).first():
                db.add(PromoCode(code=code, percent=percent, active=True))
                added_p += 1
        db.commit()
    finally:
        db.close()

    print(f"Restaurants added: {added_r} (skipped existing: {skipped}), menu items added: {added_m}, promos added: {added_p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(seed())
