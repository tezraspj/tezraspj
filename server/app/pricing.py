"""Order pricing — single source of truth on the server side."""
from .config import settings


def delivery_fee_for(subtotal: float, has_items: bool = True) -> float:
    """Free delivery automatically when the threshold is reached."""
    if not has_items or subtotal <= 0:
        return 0.0
    if subtotal >= settings.free_delivery_threshold:
        return 0.0
    return settings.delivery_fee


def calc_totals(subtotal: float, discount_percent: int = 0, has_items: bool = True) -> tuple[float, float, float]:
    """Return (delivery_fee, discount, total)."""
    discount = subtotal * max(discount_percent, 0) / 100.0
    delivery = delivery_fee_for(subtotal, has_items)
    total = (subtotal - discount + delivery) if has_items else 0.0
    return delivery, discount, total
