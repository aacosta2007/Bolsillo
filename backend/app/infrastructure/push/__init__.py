from __future__ import annotations

from functools import lru_cache

from app.application.ports import NullPushSender, PushSender
from app.core.config import Settings, get_settings


DEFAULT_SUBJECT = "mailto:admin@bolsillo.local"


def build_push_sender(settings: Settings) -> PushSender:
    """WebPushSender si hay claves VAPID; si no, NullPushSender (solo bandeja)."""
    if settings.vapid_private_key and settings.vapid_public_key:
        from app.infrastructure.push.webpush_sender import WebPushSender

        return WebPushSender(settings.vapid_private_key, settings.vapid_subject or DEFAULT_SUBJECT)
    return NullPushSender()


@lru_cache
def get_push_sender() -> PushSender:
    return build_push_sender(get_settings())
