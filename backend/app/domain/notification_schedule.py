"""Selección de usuarios por hora local (puro)."""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.domain.entities import User


def local_now(tz_name: str, now_utc: datetime) -> datetime:
    try:
        tz = ZoneInfo(tz_name)
    except Exception:  # zona desconocida -> UTC
        tz = timezone.utc
    return now_utc.astimezone(tz)


def users_due(users: list[User], now_utc: datetime) -> list[tuple[User, datetime]]:
    """Usuarios cuya hora local actual coincide con su `notify_hour`, con su hora local."""
    out = []
    for u in users:
        local = local_now(u.timezone, now_utc)
        if local.hour == u.notify_hour:
            out.append((u, local))
    return out
