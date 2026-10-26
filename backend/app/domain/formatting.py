"""Formato de montos y fechas para textos de avisos (es-CO). Puro, sin I/O."""
from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

MONTHS_ES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)
MONTHS_SHORT_ES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")


def format_cop(amount: Decimal | int | float | str) -> str:
    """Pesos enteros con punto de miles: 1234500 -> "$ 1.234.500" (negativos: "-$ 1.234")."""
    value = Decimal(str(amount)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    sign = "-" if value < 0 else ""
    return f"{sign}$ {abs(int(value)):,}".replace(",", ".")


def month_name(d: date) -> str:
    return MONTHS_ES[d.month - 1]


def short_date(d: date) -> str:
    """29 oct"""
    return f"{d.day} {MONTHS_SHORT_ES[d.month - 1]}"


def format_percent(value: float) -> str:
    """85.4 -> "85 %" (espacio fino no, espacio normal como pide el contrato)."""
    return f"{int(Decimal(str(value)).quantize(Decimal('1'), rounding=ROUND_HALF_UP))} %"
