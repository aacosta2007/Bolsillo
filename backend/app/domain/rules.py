"""Reglas de negocio puras (sin I/O)."""
from __future__ import annotations

import calendar
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from dateutil.relativedelta import relativedelta

from app.domain.entities import Account, Category
from app.domain.enums import BudgetState, CategoryKind, Frequency, TransactionType
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
