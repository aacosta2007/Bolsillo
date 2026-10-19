from __future__ import annotations

from datetime import date
from functools import lru_cache
from typing import Annotated, AsyncIterator

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.application.accounts import AccountService
from app.application.auth import AuthConfig, AuthService
from app.application.budgets import BudgetService
from app.application.categories import CategoryService
from app.application.goals import GoalService
from app.application.recurring import RecurringService
from app.application.reports import ReportService
from app.application.transactions import TransactionService
from app.core.config import Settings, get_settings
from app.domain.entities import User
from app.domain.exceptions import AuthenticationError
from app.domain.rules import first_of_month
from app.infrastructure.db.session import get_sessionmaker
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from app.infrastructure.rate_limit import LoginRateLimiter
from app.infrastructure.security.passwords import Argon2PasswordHasher
from app.infrastructure.security.tokens import JwtTokenService

bearer = HTTPBearer(auto_error=False)


@lru_cache
def get_hasher() -> Argon2PasswordHasher:
    return Argon2PasswordHasher()


@lru_cache
def get_token_service() -> JwtTokenService:
    s = get_settings()
    return JwtTokenService(s.jwt_secret, s.access_token_minutes)


@lru_cache
def get_rate_limiter() -> LoginRateLimiter:
    s = get_settings()
    return LoginRateLimiter(s.login_max_failures, s.login_window_seconds)


async def get_uow() -> AsyncIterator[SqlAlchemyUnitOfWork]:
    async with SqlAlchemyUnitOfWork(get_sessionmaker()) as uow:
        yield uow


UowDep = Annotated[SqlAlchemyUnitOfWork, Depends(get_uow)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_auth_service(uow: UowDep, settings: SettingsDep) -> AuthService:
    return AuthService(
        uow,
        get_hasher(),
        get_token_service(),
        AuthConfig(
            refresh_token_days=settings.refresh_token_days,
            default_currency=settings.default_currency,
            default_timezone=settings.default_timezone,
        ),
    )


async def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    uow: UowDep,
) -> User:
    if creds is None or creds.scheme.lower() != "bearer":
        raise AuthenticationError("No autenticado")
    user_id = get_token_service().decode_access_token(creds.credentials)
    user = await uow.users.get(user_id)
    if user is None:
        raise AuthenticationError("Sesión inválida")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
AuthSvc = Annotated[AuthService, Depends(get_auth_service)]
AccountSvc = Annotated[AccountService, Depends(lambda uow=Depends(get_uow): AccountService(uow))]
CategorySvc = Annotated[CategoryService, Depends(lambda uow=Depends(get_uow): CategoryService(uow))]
TransactionSvc = Annotated[
    TransactionService, Depends(lambda uow=Depends(get_uow): TransactionService(uow))
]
BudgetSvc = Annotated[BudgetService, Depends(lambda uow=Depends(get_uow): BudgetService(uow))]
RecurringSvc = Annotated[
    RecurringService, Depends(lambda uow=Depends(get_uow): RecurringService(uow))
]
GoalSvc = Annotated[GoalService, Depends(lambda uow=Depends(get_uow): GoalService(uow))]
ReportSvc = Annotated[ReportService, Depends(lambda uow=Depends(get_uow): ReportService(uow))]


def parse_month(value: str) -> date:
    y, m = value.split("-")
    return first_of_month(date(int(y), int(m), 1))
