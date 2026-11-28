"""Order status list."""
from fastapi import APIRouter

from ..models import OrderStatus

router = APIRouter(prefix="/api", tags=["statuses"])


@router.get("/statuses")
def list_statuses():
    return [{"value": s.value, "label": s.value} for s in OrderStatus]
