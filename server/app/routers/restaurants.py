"""Public API: restaurants and menu."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models import MenuItem, Restaurant
from ..schemas import MenuItemOut, RestaurantOut

router = APIRouter(prefix="/api", tags=["restaurants"])


def restaurant_or_404(db: Session, restaurant_id: str) -> Restaurant:
    stmt = (
        select(Restaurant)
        .options(selectinload(Restaurant.menu_items))
        .where(Restaurant.id == restaurant_id, Restaurant.active.is_(True))
    )
    rest = db.execute(stmt).scalar_one_or_none()
    if not rest:
        raise HTTPException(status_code=404, detail="Заведение не найдено")
    return rest


@router.get("/restaurants", response_model=list[RestaurantOut])
def list_restaurants(category: str | None = None, db: Session = Depends(get_db)):
    stmt = select(Restaurant).options(selectinload(Restaurant.menu_items)).where(Restaurant.active.is_(True))
    if category:
        stmt = stmt.where(Restaurant.category == category)
    stmt = stmt.order_by(Restaurant.name)
    return db.execute(stmt).scalars().all()


@router.get("/restaurants/{restaurant_id}", response_model=RestaurantOut)
def get_restaurant(restaurant_id: str, db: Session = Depends(get_db)):
    return restaurant_or_404(db, restaurant_id)


@router.get("/restaurants/{restaurant_id}/menu", response_model=list[MenuItemOut])
def get_menu(restaurant_id: str, db: Session = Depends(get_db)):
    rest = restaurant_or_404(db, restaurant_id)
    items = db.execute(
        select(MenuItem).where(
            MenuItem.restaurant_id == rest.id, MenuItem.active.is_(True)
        ).order_by(MenuItem.category, MenuItem.name)
    ).scalars().all()
    return items
