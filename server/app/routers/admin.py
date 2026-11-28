"""Admin API — protected by Bearer token (ADMIN_API_TOKEN env var).

Full management: restaurants, categories, menu (prices/photos),
orders + statuses, promo codes.
"""
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import Category, MenuItem, Order, OrderStatus, PromoCode, Restaurant
from ..schemas import (
    CategoryIn,
    CategoryOut,
    MenuItemIn,
    MenuItemOut,
    OrderOut,
    PromoIn,
    PromoOut,
    RestaurantIn,
    RestaurantOut,
    StatusPatch,
)
from ..security import compare_token

def require_admin(authorization: str | None = Header(default=None)) -> None:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    token = authorization.split(" ", 1)[1].strip()
    if not compare_token(token, settings.admin_api_token):
        raise HTTPException(status_code=401, detail="Неверный токен")


router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])

dep = [Depends(require_admin), Depends(get_db)]


def _rest_out(r: Restaurant) -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "category": r.category,
        "description": r.description,
        "image": r.image,
        "rating": r.rating,
        "delivery_time": r.delivery_time,
        "min_order": r.min_order,
        "active": r.active,
        "menu": [
            {"id": m.id, "name": m.name, "category": m.category, "price": m.price,
             "image": m.image, "description": m.description, "active": m.active}
            for m in r.menu_items
        ],
    }


# ---------- Restaurants ----------
@router.get("/restaurants")
def admin_list_restaurants(db: Session = Depends(get_db)):
    rows = db.execute(select(Restaurant).order_by(Restaurant.name)).scalars().all()
    return [_rest_out(r) for r in rows]


@router.post("/restaurants", status_code=201)
def admin_create_restaurant(payload: RestaurantIn, db: Session = Depends(get_db)):
    if db.get(Restaurant, payload.id):
        raise HTTPException(status_code=409, detail="Заведение с таким id уже существует")
    r = Restaurant(**payload.model_dump())
    db.add(r)
    db.commit()
    return _rest_out(r)


@router.put("/restaurants/{restaurant_id}")
def admin_update_restaurant(restaurant_id: str, payload: RestaurantIn, db: Session = Depends(get_db)):
    r = db.get(Restaurant, restaurant_id)
    if not r:
        raise HTTPException(status_code=404, detail="Заведение не найдено")
    for key, value in payload.model_dump().items():
        setattr(r, key, value)
    db.commit()
    return _rest_out(r)


@router.delete("/restaurants/{restaurant_id}", status_code=204)
def admin_delete_restaurant(restaurant_id: str, db: Session = Depends(get_db)):
    r = db.get(Restaurant, restaurant_id)
    if not r:
        raise HTTPException(status_code=404, detail="Заведение не найдено")
    db.delete(r)
    db.commit()


# ---------- Categories ----------
@router.get("/categories", response_model=list[CategoryOut])
def admin_list_categories(db: Session = Depends(get_db)):
    return db.execute(select(Category)).scalars().all()


@router.post("/categories", response_model=CategoryOut, status_code=201)
def admin_create_category(payload: CategoryIn, db: Session = Depends(get_db)):
    if not db.get(Restaurant, payload.restaurant_id):
        raise HTTPException(status_code=404, detail="Заведение не найдено")
    c = Category(**payload.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@router.delete("/categories/{category_id}", status_code=204)
def admin_delete_category(category_id: int, db: Session = Depends(get_db)):
    c = db.get(Category, category_id)
    if not c:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    db.delete(c)
    db.commit()


# ---------- Menu ----------
@router.get("/menu")
def admin_list_menu(restaurant_id: str | None = None, db: Session = Depends(get_db)):
    stmt = select(MenuItem)
    if restaurant_id:
        stmt = stmt.where(MenuItem.restaurant_id == restaurant_id)
    rows = db.execute(stmt.order_by(MenuItem.name)).scalars().all()
    return [
        {"id": m.id, "restaurant_id": m.restaurant_id, "name": m.name, "category": m.category,
         "price": m.price, "image": m.image, "description": m.description, "active": m.active}
        for m in rows
    ]


@router.post("/menu", status_code=201)
def admin_create_menu_item(payload: MenuItemIn, db: Session = Depends(get_db)):
    if not db.get(Restaurant, payload.restaurant_id):
        raise HTTPException(status_code=404, detail="Заведение не найдено")
    if db.get(MenuItem, payload.id):
        raise HTTPException(status_code=409, detail="Блюдо с таким id уже существует")
    m = MenuItem(**payload.model_dump())
    db.add(m)
    db.commit()
    return {"id": m.id, "ok": True}


@router.put("/menu/{item_id}")
def admin_update_menu_item(item_id: str, payload: MenuItemIn, db: Session = Depends(get_db)):
    m = db.get(MenuItem, item_id)
    if not m:
        raise HTTPException(status_code=404, detail="Блюдо не найдено")
    for key, value in payload.model_dump().items():
        setattr(m, key, value)
    db.commit()
    return {"id": m.id, "ok": True}


@router.delete("/menu/{item_id}", status_code=204)
def admin_delete_menu_item(item_id: str, db: Session = Depends(get_db)):
    m = db.get(MenuItem, item_id)
    if not m:
        raise HTTPException(status_code=404, detail="Блюдо не найдено")
    db.delete(m)
    db.commit()


# ---------- Orders & statuses ----------
@router.get("/orders", response_model=list[OrderOut])
def admin_list_orders(status: str | None = None, db: Session = Depends(get_db)):
    from .orders import _order_out

    stmt = select(Order).order_by(Order.created_at.desc())
    if status:
        stmt = stmt.where(Order.status == status)
    return [_order_out(o) for o in db.execute(stmt).scalars().all()]


@router.patch("/orders/{order_id}/status", response_model=OrderOut)
def admin_set_status(order_id: int, payload: StatusPatch, db: Session = Depends(get_db)):
    from .orders import _order_out

    valid = {s.value for s in OrderStatus}
    if payload.status not in valid:
        raise HTTPException(status_code=422, detail=f"Статус должен быть одним из: {sorted(valid)}")
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    order.status = payload.status
    db.commit()
    db.refresh(order)
    return _order_out(order)


# ---------- Promo codes ----------
@router.get("/promos", response_model=list[PromoOut])
def admin_list_promos(db: Session = Depends(get_db)):
    return db.execute(select(PromoCode).order_by(PromoCode.code)).scalars().all()


@router.post("/promos", response_model=PromoOut, status_code=201)
def admin_create_promo(payload: PromoIn, db: Session = Depends(get_db)):
    if db.execute(select(PromoCode).where(PromoCode.code == payload.code)).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Промокод уже существует")
    p = PromoCode(**payload.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.patch("/promos/{promo_id}")
def admin_update_promo(promo_id: int, payload: PromoIn, db: Session = Depends(get_db)):
    p = db.get(PromoCode, promo_id)
    if not p:
        raise HTTPException(status_code=404, detail="Промокод не найден")
    for key, value in payload.model_dump().items():
        setattr(p, key, value)
    db.commit()
    db.refresh(p)
    return p


@router.delete("/promos/{promo_id}", status_code=204)
def admin_delete_promo(promo_id: int, db: Session = Depends(get_db)):
    p = db.get(PromoCode, promo_id)
    if not p:
        raise HTTPException(status_code=404, detail="Промокод не найден")
    db.delete(p)
    db.commit()
