"""Public API: order creation with full server-side validation.

Prices, discounts and delivery are ALWAYS computed on the server from the
database — client-provided prices are ignored.
"""
import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import MenuItem, Order, OrderItem, OrderStatus, User
from ..pricing import calc_totals
from ..routers.promos import require_valid_promo
from ..routers.restaurants import restaurant_or_404
from ..schemas import OrderCreate, OrderItemOut, OrderOut
from ..telegram import send_order_notification

logger = logging.getLogger("tezraspj.orders")
router = APIRouter(prefix="/api/orders", tags=["orders"])


def _send_notification_safe(order: dict) -> None:
    """Background task: run the async Telegram sender in its own loop."""
    try:
        asyncio.run(send_order_notification(order))
    except Exception as exc:  # pragma: no cover
        logger.warning("Telegram notification failed: %s", exc)


def _order_out(order: Order) -> dict:
    return {
        "id": order.id,
        "status": order.status,
        "restaurant_id": order.restaurant_id,
        "client_name": order.client_name,
        "client_phone": order.client_phone,
        "client_address": order.client_address,
        "client_comment": order.client_comment,
        "subtotal": order.subtotal,
        "delivery_fee": order.delivery_fee,
        "discount": order.discount,
        "total": order.total,
        "promo_code": order.promo_code,
        "created_at": order.created_at,
        "items": [
            {"item_id": i.item_id, "name": i.name, "price": i.price, "qty": i.qty}
            for i in order.items
        ],
    }


@router.post("", response_model=OrderOut, status_code=201)
def create_order(
    payload: OrderCreate,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    # 1. Restaurant must exist and be active.
    restaurant = restaurant_or_404(db, payload.restaurant_id)

    # 2. Promo code (server-side list only).
    promo = require_valid_promo(db, payload.promo_code)

    # 3. Items: exist, belong to this restaurant, prices come from the DB.
    menu_rows = db.execute(
        select(MenuItem).where(
            MenuItem.restaurant_id == restaurant.id,
            MenuItem.active.is_(True),
        )
    ).scalars().all()
    menu_by_id = {m.id: m for m in menu_rows}

    subtotal = 0.0
    order_items: list[tuple[MenuItem, int]] = []
    for entry in payload.items:
        item = menu_by_id.get(entry.item_id)
        if not item:
            raise HTTPException(
                status_code=422,
                detail=f"Блюдо '{entry.item_id}' не найдено в меню ресторана «{restaurant.name}»",
            )
        subtotal += item.price * entry.qty   # server price only — entry.price ignored
        order_items.append((item, entry.qty))

    if not order_items:
        raise HTTPException(status_code=422, detail="Корзина пуста")

    # 4. Totals.
    percent = promo.percent if promo else 0
    delivery_fee, discount, total = calc_totals(subtotal, percent)

    # 5. User (best-effort, by phone).
    user = db.execute(select(User).where(User.phone == payload.client.phone.strip())).scalar_one_or_none()
    if not user:
        user = User(phone=payload.client.phone.strip(), name=payload.client.name)
        db.add(user)
        db.flush()

    # 6. Persist order + items (prices snapshot at order time).
    order = Order(
        restaurant_id=restaurant.id,
        user_id=user.id,
        client_name=payload.client.name,
        client_phone=payload.client.phone,
        client_address=payload.client.address,
        client_comment=payload.client.comment,
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        discount=discount,
        total=total,
        promo_code=promo.code if promo else None,
        status=OrderStatus.NEW.value,
    )
    db.add(order)
    db.flush()
    for item, qty in order_items:
        db.add(OrderItem(order_id=order.id, item_id=item.id, name=item.name, price=item.price, qty=qty))
    db.commit()
    db.refresh(order)

    # 7. Telegram notification (background, never blocks checkout).
    background.add_task(_send_notification_safe, _order_out(order))

    return _order_out(order)


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    return _order_out(order)
