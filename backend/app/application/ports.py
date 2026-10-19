"""Puertos que la capa de infraestructura implementa (seguridad, reloj)."""
from __future__ import annotations

from datetime import date, datetime, timezone
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


def today_in(tz_name: str) -> date:
    try:
        tz = ZoneInfo(tz_name)
    except Exception:  # zona desconocida -> UTC
        tz = timezone.utc
    return datetime.now(tz).date()
