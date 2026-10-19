import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.domain.exceptions import (
    AuthenticationError,
    BusinessRuleError,
    ConflictError,
    NotFoundError,
)

log = logging.getLogger(__name__)


def _json(status: int, detail: str, headers: dict | None = None) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": detail}, headers=headers)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def _nf(_: Request, exc: NotFoundError):
        return _json(404, exc.message)

    @app.exception_handler(ConflictError)
    async def _cf(_: Request, exc: ConflictError):
        return _json(409, exc.message)

    @app.exception_handler(BusinessRuleError)
    async def _br(_: Request, exc: BusinessRuleError):
        return _json(400, exc.message)

    @app.exception_handler(AuthenticationError)
    async def _au(_: Request, exc: AuthenticationError):
        return _json(401, exc.message, {"WWW-Authenticate": "Bearer"})

    @app.exception_handler(IntegrityError)
    async def _ie(_: Request, exc: IntegrityError):
        log.warning("IntegrityError: %s", exc.orig)
        return _json(409, "La operación entra en conflicto con datos existentes")
