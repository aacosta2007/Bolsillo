"""Envío Web Push (VAPID) con pywebpush. La llamada es bloqueante: corre en un hilo."""
from __future__ import annotations

import asyncio
import json
import logging

from pywebpush import WebPushException, webpush

from app.application.ports import PushResult, PushTarget

log = logging.getLogger(__name__)

TTL_SECONDS = 24 * 3600  # si el dispositivo está apagado, el aviso vale un día
TIMEOUT_SECONDS = 10
GONE_STATUSES = (404, 410)


class WebPushSender:
    enabled = True

    def __init__(self, private_key: str, subject: str):
        self._private_key = private_key
        self._claims = {"sub": subject}

    def _send_sync(self, target: PushTarget, payload: dict) -> PushResult:
        try:
            webpush(
                subscription_info={
                    "endpoint": target.endpoint,
                    "keys": {"p256dh": target.p256dh, "auth": target.auth},
                },
                data=json.dumps(payload, ensure_ascii=False),
                vapid_private_key=self._private_key,
                vapid_claims=dict(self._claims),  # pywebpush modifica el dict (añade aud/exp)
                ttl=TTL_SECONDS,
                timeout=TIMEOUT_SECONDS,
            )
            return PushResult.OK
        except WebPushException as exc:
            status = getattr(exc.response, "status_code", None)
            if status in GONE_STATUSES:
                return PushResult.GONE
            log.warning("Push rechazado (%s): %s", status, exc)
            return PushResult.FAILED
        except Exception:
            log.exception("Fallo inesperado enviando push")
            return PushResult.FAILED

    async def send(self, target: PushTarget, payload: dict) -> PushResult:
        return await asyncio.to_thread(self._send_sync, target, payload)
