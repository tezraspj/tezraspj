"""Public API: promo codes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import PromoCode
from ..schemas import PromoOut, PromoValidateOut

router = APIRouter(prefix="/api", tags=["promos"])


def find_promo(db: Session, code: str) -> PromoCode | None:
    stmt = select(PromoCode).where(PromoCode.code == code.strip().upper(), PromoCode.active.is_(True))
    return db.execute(stmt).scalar_one_or_none()


@router.get("/promos", response_model=list[PromoOut])
def list_promos(db: Session = Depends(get_db)):
    return db.execute(select(PromoCode).where(PromoCode.active.is_(True))).scalars().all()


@router.get("/promos/validate", response_model=PromoValidateOut)
def validate_promo(code: str, db: Session = Depends(get_db)):
    promo = find_promo(db, code)
    if not promo:
        return PromoValidateOut(valid=False, percent=0)
    return PromoValidateOut(valid=True, percent=promo.percent)


def require_valid_promo(db: Session, code: str | None) -> PromoCode | None:
    """Used by order creation: raises 422 for unknown/inactive codes."""
    if not code:
        return None
    promo = find_promo(db, code)
    if not promo:
        raise HTTPException(status_code=422, detail=f"Неверный промокод: {code}")
    return promo
