"""Generación de claves VAPID (para `python -m app.cli gen-vapid`)."""
from __future__ import annotations

import base64

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid01


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def generate_vapid_keys() -> tuple[str, str]:
    """Devuelve (public, private) en base64url sin relleno.
    public = punto P-256 sin comprimir (65 bytes), el `applicationServerKey` del navegador.
    private = escalar de 32 bytes; pywebpush lo acepta tal cual."""
    vapid = Vapid01()
    vapid.generate_keys()
    public = vapid.public_key.public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    private = vapid.private_key.private_numbers().private_value.to_bytes(32, "big")
    return _b64url(public), _b64url(private)
