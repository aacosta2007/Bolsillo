from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_exception_handlers
from app.api.v1 import api_router
from app.application.auth import AuthConfig, AuthService
from app.application.recurring import run_pending_for_all_users
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.infrastructure.db.session import dispose_engine, get_sessionmaker
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from app.infrastructure.push import get_push_sender
from app.infrastructure.scheduler import build_scheduler, uow_factory
from app.infrastructure.security.passwords import Argon2PasswordHasher
from app.infrastructure.security.tokens import JwtTokenService

log = logging.getLogger("bolsillo")


async def ensure_initial_user() -> None:
    s = get_settings()
    if not (s.initial_user_email and s.initial_user_password):
        return
    async with SqlAlchemyUnitOfWork(get_sessionmaker()) as uow:
        if await uow.users.count() > 0:
            return
        svc = AuthService(
            uow,
            Argon2PasswordHasher(),
            JwtTokenService(s.jwt_secret, s.access_token_minutes),
            AuthConfig(s.refresh_token_days, s.default_currency, s.default_timezone),
        )
        await svc.create_user(s.initial_user_email, s.initial_user_password)
        log.info("Usuario inicial creado: %s", s.initial_user_email)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    scheduler = build_scheduler()
    try:
        await ensure_initial_user()
    except Exception:
        log.exception("No se pudo crear el usuario inicial")
    try:
        await run_pending_for_all_users(uow_factory, get_push_sender())
    except Exception:
        log.exception("Fallo ejecutando recurrentes al arrancar")
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)
        await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Bolsillo API",
        version="1.0.0",
        docs_url="/api/v1/docs",
        openapi_url="/api/v1/openapi.json",
        redoc_url=None,
        lifespan=lifespan,
    )
    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    register_exception_handlers(app)
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
