"""Puertos que la capa de infraestructura implementa (seguridad, reloj)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import StrEnum
from typing import Protocol
from uuid import UUID
from zoneinfo import ZoneInfo


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...
    def verify(self, password_hash: str, password: str) -> bool: ...
    def needs_rehash(self, password_hash: str) -> bool: ...


class TokenService(Protocol):
    def create_access_token(self, user_id: UUID) -> tuple[str, int]:
        """Devuelve (token, expires_in_segundos)."""
        ...

    def decode_access_token(self, token: str) -> UUID:
        """Lanza AuthenticationError si es inválido o expiró."""
        ...

    def new_refresh_token(self) -> tuple[str, str]:
        """Devuelve (token_en_claro, hash)."""
        ...

    def hash_refresh_token(self, raw: str) -> str: ...


class PushResult(StrEnum):
    OK = "ok"
    GONE = "gone"  # 404/410: la suscripción ya no existe y debe borrarse
    FAILED = "failed"


@dataclass(frozen=True)
class PushTarget:
    endpoint: str
    p256dh: str
    auth: str


class PushSender(Protocol):
    @property
    def enabled(self) -> bool:
        """False si no hay claves VAPID (solo bandeja)."""
        ...

    async def send(self, target: PushTarget, payload: dict) -> PushResult:
        """Envía un push cifrado. Nunca lanza: los errores se devuelven como PushResult."""
        ...


class NullPushSender:
    """Sin claves VAPID: no envía nada; la bandeja sigue funcionando."""

    enabled = False

    async def send(self, target: PushTarget, payload: dict) -> PushResult:
        return PushResult.FAILED


def today_in(tz_name: str) -> date:
    try:
        tz = ZoneInfo(tz_name)
    except Exception:  # zona desconocida -> UTC
        tz = timezone.utc
    return datetime.now(tz).date()
