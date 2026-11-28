"""Pydantic schemas (API contracts)."""
import re
from datetime import datetime
from typing import Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

PHONE_RE = re.compile(r"^(?:\+?992\d{9}|\d{9}|8\d{10})$")
NAME_RE = re.compile(r"^[A-Za-zА-Яа-яЁёғқҷҳҒҚҷҲ\s'-]{2,50}$")


# ---------- Menu / restaurants ----------
class MenuItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    category: str
    price: float
    image: str
    description: str


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    restaurant_id: str


class RestaurantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    category: str
    description: str
    image: str
    rating: float
    deliveryTime: str = Field(validation_alias="delivery_time")
    minOrder: str = Field(validation_alias="min_order")
    menu: list[MenuItemOut] = Field(
        default_factory=list,
        validation_alias=AliasChoices("menu", "menu_items"),
    )


class RestaurantIn(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=120)
    category: str = Field(min_length=1, max_length=64)
    description: str = ""
    image: str = ""
    rating: float = Field(default=0.0, ge=0, le=5)
    delivery_time: str = "20-30 мин"
    min_order: str = "0 смн"
    active: bool = True


class MenuItemIn(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    restaurant_id: str
    name: str = Field(min_length=1, max_length=160)
    category: str = ""
    price: float = Field(gt=0)
    image: str = ""
    description: str = ""
    active: bool = True


class CategoryIn(BaseModel):
    restaurant_id: str
    name: str = Field(min_length=1, max_length=80)


# ---------- Promo ----------
class PromoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    percent: int
    active: bool


class PromoIn(BaseModel):
    code: str = Field(min_length=3, max_length=32)
    percent: int = Field(gt=0, le=100)
    active: bool = True

    @field_validator("code")
    @classmethod
    def normalize_code(cls, v: str) -> str:
        return v.strip().upper()


class PromoValidateOut(BaseModel):
    valid: bool
    percent: int = 0


# ---------- Orders ----------
class ClientInfo(BaseModel):
    name: str = Field(min_length=2, max_length=50)
    phone: str = Field(min_length=5, max_length=32)
    address: str = Field(min_length=5, max_length=200)
    comment: str = Field(default="", max_length=500)

    @field_validator("name")
    @classmethod
    def valid_name(cls, v: str) -> str:
        v = v.strip()
        if not NAME_RE.match(v):
            raise ValueError("Имя: 2–50 букв (допустимы пробелы и дефис)")
        return v

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, v: str) -> str:
        digits = re.sub(r"\D", "", v)
        if not (PHONE_RE.match(digits) or PHONE_RE.match(v.strip().replace(" ", ""))):
            raise ValueError("Телефон: +992 XX XXX XXX (или 9XXXXXXXXX)")
        return v.strip()

    @field_validator("address")
    @classmethod
    def valid_address(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 5:
            raise ValueError("Адрес: от 5 символов (улица, дом, ориентир)")
        return v


class OrderItemIn(BaseModel):
    item_id: str
    qty: int = Field(gt=0, le=100)
    # Accepted but deliberately ignored: prices are computed server-side.
    price: Optional[float] = None


class OrderCreate(BaseModel):
    restaurant_id: str
    client: ClientInfo
    items: list[OrderItemIn] = Field(min_length=1)
    promo_code: Optional[str] = None


class OrderItemOut(BaseModel):
    item_id: str
    name: str
    price: float
    qty: int


class OrderOut(BaseModel):
    id: int
    status: str
    restaurant_id: str
    client_name: str
    client_phone: str
    client_address: str
    client_comment: str
    subtotal: float
    delivery_fee: float
    discount: float
    total: float
    promo_code: Optional[str]
    created_at: datetime
    items: list[OrderItemOut] = []


class StatusPatch(BaseModel):
    status: str


# ---------- Users ----------
class UserIn(BaseModel):
    phone: str = Field(min_length=5, max_length=32)
    name: str = Field(default="", max_length=80)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phone: str
    name: str
    created_at: datetime
