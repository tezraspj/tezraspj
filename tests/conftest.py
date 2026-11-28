"""Shared pytest fixtures. Environment is configured BEFORE app imports."""
import sys
import tempfile
from pathlib import Path

# Ensure server/ is importable and use an isolated test database.
SERVER_DIR = Path(__file__).resolve().parent.parent / "server"
sys.path.insert(0, str(SERVER_DIR))

_tmpdir = tempfile.mkdtemp(prefix="tezraspj_test_")
import os  # noqa: E402

os.environ["DATABASE_URL"] = f"sqlite:///{_tmpdir}/test.db"
os.environ["ADMIN_API_TOKEN"] = "test-admin-token"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["TELEGRAM_BOT_TOKEN"] = ""
os.environ["TELEGRAM_CHAT_ID"] = ""
os.environ["ENVIRONMENT"] = "test"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
import seed as seed_module  # noqa: E402

ADMIN_HEADERS = {"Authorization": "Bearer test-admin-token"}


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    code = seed_module.seed()
    assert code == 0, "seeding failed"
    # A default promo for tests (idempotent).
    from app.db import SessionLocal
    from app.models import PromoCode
    from sqlalchemy import select

    db = SessionLocal()
    try:
        if not db.execute(select(PromoCode).where(PromoCode.code == "SALE10")).scalar_one_or_none():
            db.add(PromoCode(code="SALE10", percent=10, active=True))
            db.commit()
    finally:
        db.close()
    yield


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def sample_order(client):
    """Build a valid order payload from real API data."""
    restaurants = client.get("/api/restaurants").json()
    rest = restaurants[0]
    item = rest["menu"][0]
    return {
        "restaurant_id": rest["id"],
        "promo_code": None,
        "client": {
            "name": "Тест Клиент",
            "phone": "+992 90 111 22 33",
            "address": "Улица Рудаки, дом 1",
            "comment": "позвонить за 5 минут",
        },
        "items": [{"item_id": item["id"], "qty": 1}],
        "_item": item,
        "_restaurant": rest,
    }
