"""Textos de los avisos (puro). Cada función devuelve (title, body, url)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.domain.formatting import format_cop, format_percent, month_name, short_date


@dataclass(frozen=True)
class Message:
    title: str
    body: str
    url: str


def budget_warning(category: str, percent: float, remaining: Decimal, days_left: int | None) -> Message:
    """`days_left`: días que quedan del mes (incluye hoy); None si el mes ya no es el actual."""
    body = f"Te quedan {format_cop(max(remaining, Decimal(0)))} de tu presupuesto"
    if days_left is not None and days_left > 0:
        body += f" para {days_left} {'día' if days_left == 1 else 'días'}"
    return Message(f"{category} llegó al {format_percent(percent)}", body + ".", "/presupuestos")


def budget_exceeded(category: str, spent: Decimal, limit: Decimal) -> Message:
    over = spent - limit
    return Message(
        f"{category} excedido: te pasaste por {format_cop(over)}",
        f"Gastaste {format_cop(spent)} de un presupuesto de {format_cop(limit)}.",
        "/presupuestos",
    )


def upcoming_recurring(
    name: str, amount: Decimal, account: str | None, is_income: bool, day: date, days_before: int
) -> Message:
    when = "Hoy" if days_before == 0 else "Mañana" if days_before == 1 else f"En {days_before} días"
    title = f"{when}: {name} {format_cop(amount)}"
    if account:
        title += f" {'en' if is_income else 'desde'} {account}"
    kind = "Ingreso" if is_income else "Gasto"
    return Message(title, f"{kind} recurrente programado para el {short_date(day)}.", "/metas?tab=recurrentes")


def payday(amount: Decimal, available_per_day: Decimal | None, period_end: date | None) -> Message:
    title = f"Llegó tu quincena: {format_cop(amount)}"
    if available_per_day is not None and available_per_day > 0 and period_end is not None:
        body = f"Puedes gastar ≈ {format_cop(available_per_day)} por día hasta el {short_date(period_end)}."
    else:
        body = "Revisa cómo va tu quincena en el inicio."
    return Message(title, body, "/")


def monthly_report(report_month: date) -> Message:
    return Message(
        f"Tu reporte de {month_name(report_month)} está listo",
        "Revisa en qué gastaste y cuánto ahorraste el mes pasado.",
        f"/reportes?tab=mes&mes={report_month.strftime('%Y-%m')}",
    )


def test_message() -> Message:
    return Message("Bolsillo: aviso de prueba", "Las notificaciones funcionan en este dispositivo.", "/")
