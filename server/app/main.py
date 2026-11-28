"""FastAPI application factory."""
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .rate_limit import rate_limit_middleware
from .routers import admin, orders, promos, restaurants, statuses, users

logging.basicConfig(level=logging.INFO)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="API доставки еды в Пенджикенте (заведения, меню, заказы, промокоды)",
    )

    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def rate_limit(request: Request, call_next):
        return await rate_limit_middleware(request, call_next)

    app.include_router(restaurants.router)
    app.include_router(orders.router)
    app.include_router(promos.router)
    app.include_router(users.router)
    app.include_router(statuses.router)
    app.include_router(admin.router)

    @app.get("/api/health", tags=["system"])
    def health():
        return {"status": "ok", "app": settings.app_name, "environment": settings.environment}

    return app


app = create_app()
