from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from app.application.ports import PasswordHasher, TokenService
from app.domain.defaults import DEFAULT_EXPENSE_CATEGORIES, DEFAULT_INCOME_CATEGORIES
from app.domain.entities import Category, RefreshToken, User, utcnow
from app.domain.enums import CategoryKind
from app.domain.exceptions import (
    AuthenticationError,
    BusinessRuleError,
    ConflictError,
    NotFoundError,
)
from app.domain.repositories import UnitOfWork


@dataclass
class AuthConfig:
    refresh_token_days: int = 30
    default_currency: str = "COP"
    default_timezone: str = "America/Bogota"


@dataclass
class Session:
    access_token: str
    expires_in: int
    refresh_token: str


class AuthService:
    def __init__(
        self, uow: UnitOfWork, hasher: PasswordHasher, tokens: TokenService, config: AuthConfig
    ):
        self.uow = uow
        self.hasher = hasher
        self.tokens = tokens
        self.config = config

    # ---- usuarios ----
    async def create_user(
        self,
        email: str,
        password: str,
        display_name: str | None = None,
        currency: str | None = None,
        timezone: str | None = None,
    ) -> User:
        email = email.strip().lower()
        if await self.uow.users.get_by_email(email):
            raise ConflictError("Ya existe un usuario con ese correo")
        if len(password) < 8:
            raise BusinessRuleError("La contraseña debe tener al menos 8 caracteres")
        user = User(
            email=email,
            password_hash=self.hasher.hash(password),
            display_name=display_name,
            currency=currency or self.config.default_currency,
            timezone=timezone or self.config.default_timezone,
        )
        await self.uow.users.add(user)
        cats = [
            Category(user_id=user.id, name=n, kind=CategoryKind.EXPENSE, icon=i, color=c)
            for n, i, c in DEFAULT_EXPENSE_CATEGORIES
        ] + [
            Category(user_id=user.id, name=n, kind=CategoryKind.INCOME, icon=i, color=c)
            for n, i, c in DEFAULT_INCOME_CATEGORIES
        ]
        await self.uow.categories.add_many(cats)
        await self.uow.commit()
        return user

    async def get_user(self, user_id: UUID) -> User:
        user = await self.uow.users.get(user_id)
        if user is None:
            raise AuthenticationError("Sesión inválida")
        return user

    async def update_profile(self, user_id: UUID, changes: dict) -> User:
        user = await self.get_user(user_id)
        for key in ("currency", "timezone", "display_name"):
            if key in changes:
                setattr(user, key, changes[key])
        await self.uow.users.update(user)
        await self.uow.commit()
        return user

    async def change_password(self, user_id: UUID, current: str, new: str) -> None:
        user = await self.get_user(user_id)
        if not self.hasher.verify(user.password_hash, current):
            raise BusinessRuleError("La contraseña actual es incorrecta")
        if len(new) < 8:
            raise BusinessRuleError("La nueva contraseña debe tener al menos 8 caracteres")
        user.password_hash = self.hasher.hash(new)
        await self.uow.users.update(user)
        await self.uow.tokens.revoke_all_for_user(user.id)
        await self.uow.commit()

    # ---- sesión ----
    async def _open_session(self, user: User) -> Session:
        access, expires_in = self.tokens.create_access_token(user.id)
        raw, hashed = self.tokens.new_refresh_token()
        await self.uow.tokens.add(
            RefreshToken(
                user_id=user.id,
                token_hash=hashed,
                expires_at=utcnow() + timedelta(days=self.config.refresh_token_days),
            )
        )
        await self.uow.tokens.delete_expired(utcnow())
        await self.uow.commit()
        return Session(access, expires_in, raw)

    async def login(self, email: str, password: str) -> Session:
        user = await self.uow.users.get_by_email(email.strip().lower())
        if user is None:
            # Gasta el mismo tiempo que una verificación real
            self.hasher.verify(self.hasher.hash("dummy-password"), password)
            raise AuthenticationError("Correo o contraseña incorrectos")
        if not self.hasher.verify(user.password_hash, password):
            raise AuthenticationError("Correo o contraseña incorrectos")
        if self.hasher.needs_rehash(user.password_hash):
            user.password_hash = self.hasher.hash(password)
            await self.uow.users.update(user)
        return await self._open_session(user)

    async def refresh(self, raw_token: str | None) -> Session:
        if not raw_token:
            raise AuthenticationError("Sesión expirada")
        stored = await self.uow.tokens.get_by_hash(self.tokens.hash_refresh_token(raw_token))
        if stored is None or stored.revoked or stored.expires_at <= utcnow():
            raise AuthenticationError("Sesión expirada")
        user = await self.uow.users.get(stored.user_id)
        if user is None:
            raise AuthenticationError("Sesión expirada")
        await self.uow.tokens.revoke(stored.id)  # rotación: el token usado deja de valer
        return await self._open_session(user)

    async def logout(self, raw_token: str | None) -> None:
        if not raw_token:
            return
        stored = await self.uow.tokens.get_by_hash(self.tokens.hash_refresh_token(raw_token))
        if stored is not None and not stored.revoked:
            await self.uow.tokens.revoke(stored.id)
            await self.uow.commit()

    def authenticate_access_token(self, token: str) -> UUID:
        return self.tokens.decode_access_token(token)


__all__ = ["AuthService", "AuthConfig", "Session", "NotFoundError"]
