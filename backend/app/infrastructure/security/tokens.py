import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt

from app.domain.exceptions import AuthenticationError


class JwtTokenService:
    ALGORITHM = "HS256"

    def __init__(self, secret: str, access_minutes: int = 15):
        self._secret = secret
        self._access_minutes = access_minutes

    def create_access_token(self, user_id: UUID) -> tuple[str, int]:
        now = datetime.now(timezone.utc)
        exp = now + timedelta(minutes=self._access_minutes)
        token = jwt.encode(
            {"sub": str(user_id), "iat": now, "exp": exp, "typ": "access"},
            self._secret,
            algorithm=self.ALGORITHM,
        )
        return token, self._access_minutes * 60

    def decode_access_token(self, token: str) -> UUID:
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self.ALGORITHM])
            if payload.get("typ") != "access":
                raise AuthenticationError("Token inválido")
            return UUID(payload["sub"])
        except (jwt.PyJWTError, KeyError, ValueError):
            raise AuthenticationError("Sesión inválida o expirada") from None

    def new_refresh_token(self) -> tuple[str, str]:
        raw = secrets.token_urlsafe(48)
        return raw, self.hash_refresh_token(raw)

    def hash_refresh_token(self, raw: str) -> str:
        return hashlib.sha256(raw.encode()).hexdigest()
