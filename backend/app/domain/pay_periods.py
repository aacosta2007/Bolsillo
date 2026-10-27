"""Quincenas de pago (puro, sin I/O): fechas de pago, periodos y métricas derivadas."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum
from typing import Iterable

from app.domain.entities import RecurringRule
from app.domain.rules import effective_date, first_nominal_on_or_after, last_of_month, next_nominal_after, q2

MIN_PAYDAY_GAP_DAYS = 3  # dos fechas de pago a 3 días o menos se fusionan (se conserva la primera)
MAX_RULE_OCCURRENCES = 5000  # tope de seguridad por regla (p. ej. una diaria con años de historia)
SAVINGS_MARGIN = Decimal("0.10")  # net < 10 % del ingreso -> "justo"


class PeriodSource(str, Enum):
    PAYCHECK = "paycheck"
    CALENDAR = "calendar"


class PeriodStatus(str, Enum):
    IN_PROGRESS = "en_curso"
    SAVING = "ahorro"
    TIGHT = "justo"
    DEFICIT = "deficit"
    CALENDAR = "calendario"  # periodo cerrado de respaldo: sin juicio, no se sabe cuánto es el sueldo


@dataclass(kw_only=True)
class Payday:
    date: date
    amount: Decimal
    note: str | None = None


@dataclass(kw_only=True)
class PeriodSpan:
    start: date
    end: date  # inclusive
    source: PeriodSource


@dataclass(kw_only=True)
class PayPeriod:
    start: date
    end: date
    days: int
    days_elapsed: int
    days_remaining: int
    in_progress: bool
    source: PeriodSource
    income: Decimal
    salary_income: Decimal
    extra_income: Decimal
    expense: Decimal
    net: Decimal
    spent_per_day: Decimal
    available_per_day: Decimal | None
    spent_percent: float
    time_percent: float
    status: PeriodStatus
    by_category: list = field(default_factory=list)  # la capa de aplicación la rellena


def paydays(rules: list[RecurringRule], today: date) -> list[Payday]:
    """Fechas de pago efectivas (unión sin duplicados de las reglas de sueldo activas), ordenadas.

    Se calculan desde el calendario de cada regla, no desde los movimientos, y se generan hasta la
    primera posterior a `today` (necesaria para cerrar el periodo en curso y para next_payday).
    Varias reglas el mismo día suman monto; la nota es la de la primera regla."""
    found: dict[date, Payday] = {}
    for rule in rules:
        if not (rule.active and rule.is_paycheck):
            continue
        nominal = first_nominal_on_or_after(
            rule.start_date, rule.frequency, rule.interval, rule.days_of_month, rule.start_date
        )
        for _ in range(MAX_RULE_OCCURRENCES):
            d = effective_date(nominal, rule.weekend_adjust)
            if rule.end_date is not None and d > rule.end_date:
                break
            if d in found:
                found[d].amount += rule.amount
            else:
                found[d] = Payday(date=d, amount=rule.amount, note=rule.note)
            if d > today:
                break
            nominal = next_nominal_after(
                rule.start_date, rule.frequency, rule.interval, rule.days_of_month, nominal
            )
    return [found[d] for d in sorted(found)]


def merge_pay_dates(real_past: Iterable[date], rule_dates: Iterable[date], today: date) -> list[date]:
    """Fechas de pago = sueldos reales pasados (<= hoy) + fechas de calendario futuras (> hoy).

    Se unen sin duplicados y, si dos fechas quedan a 3 días o menos, se conserva solo la primera
    (un ajuste o un bono no parten la quincena). Un pago programado pasado que no llegó no cuenta."""
    candidates = sorted({d for d in real_past if d <= today} | {d for d in rule_dates if d > today})
    merged: list[date] = []
    for d in candidates:
        if not merged or (d - merged[-1]).days > MIN_PAYDAY_GAP_DAYS:
            merged.append(d)
    return merged


def calendar_span(d: date) -> PeriodSpan:
    """Respaldo de calendario: 1–15 o 16–fin de mes, la que contiene `d`."""
    if d.day <= 15:
        return PeriodSpan(start=d.replace(day=1), end=d.replace(day=15), source=PeriodSource.CALENDAR)
    return PeriodSpan(start=d.replace(day=16), end=last_of_month(d), source=PeriodSource.CALENDAR)


def build_spans(pay_dates: list[date], today: date, count: int) -> list[PeriodSpan]:
    """`count` periodos de la más reciente a la más antigua; el primero contiene `today`.

    Periodo de sueldo: de una fecha de pago al día anterior a la siguiente. Antes del primer pago
    (o sin sueldo) se usa el calendario, recortado para no solaparse con el primer periodo de sueldo."""
    pay_dates = sorted(set(pay_dates))
    started = [p for p in pay_dates if p <= today]
    later = [p for p in pay_dates if p > today]
    if started:
        start = started[-1]
        end = later[0] - timedelta(days=1) if later else calendar_span(today).end  # regla terminada
        current = PeriodSpan(start=start, end=max(end, start), source=PeriodSource.PAYCHECK)
    else:
        current = calendar_span(today)
        if later:
            current.end = min(current.end, later[0] - timedelta(days=1))
    spans = [current]
    while len(spans) < count:
        last = spans[-1]
        before = [p for p in pay_dates if p < last.start]
        if last.source == PeriodSource.PAYCHECK and before:
            spans.append(
                PeriodSpan(start=before[-1], end=last.start - timedelta(days=1), source=PeriodSource.PAYCHECK)
            )
        else:
            span = calendar_span(last.start - timedelta(days=1))
            span.end = min(span.end, last.start - timedelta(days=1))  # no solapar con el periodo de sueldo
            spans.append(span)
    return spans


def period_metrics(
    span: PeriodSpan, today: date, income: Decimal, expense: Decimal, salary_income: Decimal = Decimal(0)
) -> PayPeriod:
    """Métricas del periodo según el contrato (dinero con 2 decimales, porcentajes con 1).

    `income` es el total de ingresos; `salary_income` la parte que es sueldo (el resto es extra)."""
    salary_income = min(salary_income, income)
    days = (span.end - span.start).days + 1
    in_progress = span.start <= today <= span.end
    days_elapsed = (today - span.start).days + 1 if in_progress else days
    days_remaining = days - days_elapsed + 1 if in_progress else 0
    net = income - expense
    if in_progress:
        status = PeriodStatus.IN_PROGRESS
    elif span.source == PeriodSource.CALENDAR:
        status = PeriodStatus.CALENDAR
    elif net < 0:
        status = PeriodStatus.DEFICIT
    elif income == 0 or net < income * SAVINGS_MARGIN:  # sin ingresos no hay ahorro que mostrar
        status = PeriodStatus.TIGHT
    else:
        status = PeriodStatus.SAVING
    return PayPeriod(
        start=span.start,
        end=span.end,
        days=days,
        days_elapsed=days_elapsed,
        days_remaining=days_remaining,
        in_progress=in_progress,
        source=span.source,
        income=q2(income),
        salary_income=q2(salary_income),
        extra_income=q2(income - salary_income),
        expense=q2(expense),
        net=q2(net),
        spent_per_day=q2(expense / days_elapsed),
        available_per_day=q2(max(net, Decimal(0)) / days_remaining) if in_progress else None,
        spent_percent=round(float(expense / income * 100), 1) if income > 0 else 0.0,
        time_percent=round(days_elapsed / days * 100, 1),
        status=status,
    )
