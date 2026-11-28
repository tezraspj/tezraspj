"""Public API: users (simple loyalty/contacts)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User
from ..schemas import UserIn, UserOut

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("", response_model=UserOut)
def create_or_get_user(payload: UserIn, db: Session = Depends(get_db)):
    phone = payload.phone.strip()
    user = db.execute(select(User).where(User.phone == phone)).scalar_one_or_none()
    if user:
        if payload.name and not user.name:
            user.name = payload.name
            db.commit()
        return user
    user = User(phone=phone, name=payload.name.strip())
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user
