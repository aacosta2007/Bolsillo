"""Reglas de negocio puras (sin I/O)."""
from __future__ import annotations

import calendar
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from dateutil.relativedelta import relativedelta

from app.domain.entities import Account, Category
from app.domain.enums import BudgetState, CategoryKind, Frequency, TransactionType, WeekendAdjust
from app.domain.exceptions import BusinessRuleError

CENT = Decimal("0.01")


def q2(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


# ---------- Transacciones ----------
def validate_transaction(
    *,
    type: TransactionType,
    amount: Decimal,
    account_id: UUID,
    category_id: UUID | None,
    transfer_account_id: UUID | None,
    category: Category | None,
    check_archived: list[Account],
) -> None:
    """Lanza BusinessRuleError si el movimiento viola alguna regla.

    `check_archived` son las cuentas que no deben estar archivadas (las nuevas o modificadas).
    """
    if amount is None or amount <= 0:
        raise BusinessRuleError("El monto debe ser mayor que cero")
    if type == TransactionType.TRANSFER:
        if transfer_account_id is None:
            raise BusinessRuleError("La transferencia requiere una cuenta destino")
        if transfer_account_id == account_id:
            raise BusinessRuleError("La cuenta destino debe ser distinta de la cuenta origen")
        if category_id is not None:
            raise BusinessRuleError("Las transferencias no llevan categoría")
    else:
        if transfer_account_id is not None:
            raise BusinessRuleError("Solo las transferencias llevan cuenta destino")
        if category_id is None or category is None:
            raise BusinessRuleError("La categoría es obligatoria")
        if category.kind != CategoryKind(type.value):
            raise BusinessRuleError("El tipo de la categoría no coincide con el tipo del movimiento")
    for acc in check_archived:
        if acc.archived:
            raise BusinessRuleError(f"La cuenta «{acc.name}» está archivada y no acepta movimientos nuevos")


# ---------- Presupuestos ----------
def budget_status(
    amount_limit: Decimal, spent: Decimal, threshold: Decimal
) -> tuple[Decimal, float, BudgetState]:
    """Devuelve (remaining, percent, status)."""
    remaining = amount_limit - spent
    percent = round(float(spent / amount_limit * 100), 1) if amount_limit > 0 else 0.0
    if spent > amount_limit:
        state = BudgetState.EXCEEDED
    elif amount_limit > 0 and spent / amount_limit >= threshold:
        state = BudgetState.WARNING
    else:
        state = BudgetState.OK
    return remaining, percent, state


def first_of_month(d: date) -> date:
    return d.replace(day=1)


def last_of_month(d: date) -> date:
    return d.replace(day=calendar.monthrange(d.year, d.month)[1])


def add_months(d: date, months: int) -> date:
    return d + relativedelta(months=months)


# ---------- Recurrentes ----------
def occurrence(start: date, frequency: Frequency, interval: int, n: int) -> date:
    """n-ésima ocurrencia (n=0 es start). Mensual/anual se calculan desde start para no
    arrastrar el recorte de fin de mes (31 ene -> 28 feb -> 31 mar)."""
    k = n * interval
    if frequency == Frequency.DAILY:
        return start + timedelta(days=k)
    if frequency == Frequency.WEEKLY:
        return start + timedelta(weeks=k)
    if frequency == Frequency.MONTHLY:
        return start + relativedelta(months=k)
    return start + relativedelta(years=k)


def next_after(start: date, frequency: Frequency, interval: int, current: date) -> date:
    """Primera ocurrencia estrictamente posterior a `current`."""
    interval = max(1, interval)
    if current < start:
        return start
    days = (current - start).days
    if frequency == Frequency.DAILY:
        n = days // interval
    elif frequency == Frequency.WEEKLY:
        n = days // (7 * interval)
    elif frequency == Frequency.MONTHLY:
        n = ((current.year - start.year) * 12 + current.month - start.month) // interval
    else:
        n = (current.year - start.year) // interval
    n = max(0, n - 1)
    while occurrence(start, frequency, interval, n) <= current:
        n += 1
    return occurrence(start, frequency, interval, n)


# ---- Días del mes (monthly_days) ----
LAST = 32  # centinela interno de «L» (último día del mes); ordena después de 1..31
MAX_DAYS_OF_MONTH = 3


def parse_days_of_month(raw: str | None) -> tuple[int, ...]:
    """Valida y normaliza "15,L": 1 a 3 valores (1-31 o L), sin repetir, ascendentes y L al final."""
    if raw is None or not str(raw).strip():
        raise BusinessRuleError("days_of_month es obligatorio con la frecuencia monthly_days")
    days: list[int] = []
    for part in str(raw).split(","):
        part = part.strip().upper()
        if part == "L":
            days.append(LAST)
        elif part.isascii() and part.isdigit() and 1 <= int(part) <= 31:
            days.append(int(part))
        else:
            raise BusinessRuleError(f"Día del mes inválido: «{part}» (use 1-31 o L)")
    if len(days) > MAX_DAYS_OF_MONTH:
        raise BusinessRuleError("days_of_month admite como máximo 3 valores")
    if len(set(days)) != len(days):
        raise BusinessRuleError("days_of_month no admite valores repetidos")
    return tuple(sorted(days))


def normalize_days_of_month(raw: str | None) -> str:
    return ",".join("L" if d == LAST else str(d) for d in parse_days_of_month(raw))


def month_occurrences(year: int, month: int, days: tuple[int, ...]) -> list[date]:
    """Fechas nominales del mes: el día inexistente se recorta al último (30 -> 28 en feb) y las
    fechas que coinciden se generan una sola vez ("30,L" en febrero)."""
    last = calendar.monthrange(year, month)[1]
    return sorted({date(year, month, last if d == LAST else min(d, last)) for d in days})


def effective_date(nominal: date, weekend_adjust: WeekendAdjust | str) -> date:
    """Fecha real del movimiento: con previous_business_day, sábado/domingo -> viernes anterior."""
    if WeekendAdjust(weekend_adjust) == WeekendAdjust.PREVIOUS_BUSINESS_DAY:
        wd = nominal.weekday()  # 5 = sábado, 6 = domingo
        if wd >= 5:
            return nominal - timedelta(days=wd - 4)
    return nominal


def first_nominal_on_or_after(
    start: date, frequency: Frequency, interval: int, days_of_month: str | None, d: date
) -> date:
    """Primera ocurrencia nominal >= `d` (y >= start). Para las frecuencias clásicas con
    d <= start es el propio start."""
    d = max(d, start)
    if Frequency(frequency) != Frequency.MONTHLY_DAYS:
        return d if d == start else next_after(start, frequency, interval, d - timedelta(days=1))
    days = parse_days_of_month(days_of_month)
    year, month = d.year, d.month
    while True:
        for occ in month_occurrences(year, month, days):
            if occ >= d:
                return occ
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)


def next_nominal_after(
    start: date, frequency: Frequency, interval: int, days_of_month: str | None, current: date
) -> date:
    """Primera ocurrencia nominal estrictamente posterior a `current`, para todas las frecuencias."""
    return first_nominal_on_or_after(start, frequency, interval, days_of_month, current + timedelta(days=1))


def monthly_equivalent(
    amount: Decimal, frequency: Frequency, interval: int, days_of_month: str | None
) -> Decimal:
    """Equivalente mensual aproximado del monto de una regla (para «≈ $ X al mes»)."""
    interval = max(1, interval)
    f = Frequency(frequency)
    if f == Frequency.MONTHLY_DAYS:
        value = amount * len(parse_days_of_month(days_of_month))
    elif f == Frequency.MONTHLY:
        value = amount / interval
    elif f == Frequency.WEEKLY:
        value = amount * 52 / 12 / interval
    elif f == Frequency.DAILY:
        value = amount * 365 / 12 / interval
    else:
        value = amount / 12 / interval
    return q2(value)


# ---------- Metas ----------
def months_remaining(today: date, target: date) -> int:
    months = (target.year - today.year) * 12 + (target.month - today.month)
    return max(1, months)


def monthly_needed(
    target_amount: Decimal, saved: Decimal, target_date: date | None, today: date
) -> Decimal | None:
    if target_date is None or saved >= target_amount:
        return None
    return q2((target_amount - saved) / months_remaining(today, target_date))


def goal_percent(target_amount: Decimal, saved: Decimal) -> float:
    if target_amount <= 0:
        return 0.0
    return round(float(saved / target_amount * 100), 1)
