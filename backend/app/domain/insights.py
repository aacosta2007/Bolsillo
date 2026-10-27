"""Observaciones del reporte mensual, calculadas por reglas (no IA). Puro, sin I/O.

Cada regla devuelve cero o una observación con una relevancia (`score`); se ordenan por relevancia
descendente y se entregan entre 2 y 6. Las reglas `savings_rate` y `no_spend_days` siempre generan
una observación, así que el mínimo de 2 está garantizado.

Relevancia (mayor primero): presupuesto excedido 100 · quincena en déficit 95 · tasa de ahorro negativa 98 ·
mayor alza de categoría 90 · récord de ahorro 85 · ingreso nuevo 80 · tasa de ahorro < 20 % 65-75 ·
mayor baja de categoría 70 · tasa de ahorro >= 20 % 60 · días sin gasto 40-55 · quincena más corta/larga 45.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from app.domain.formatting import (
    format_cop,
    format_percent,
    format_percent1,
    month_name,
    short_date,
)
from app.domain.monthly_report import Insight, InsightKind, MonthlyReport, Tone
from app.domain.enums import BudgetState
from app.domain.pay_periods import PeriodSource
from app.domain.rules import add_months

MIN_CHANGE_PCT = 10.0  # una categoría solo es noticia si cambió >= 10 %...
MIN_CHANGE_AMOUNT = Decimal(20000)  # ...y al menos $ 20.000
SAVINGS_TARGET = 20.0  # meta sugerida de tasa de ahorro (%)
MIN_INSIGHTS = 2
MAX_NAMES_LISTED = 3  # en la observación de presupuestos excedidos
MAX_INSIGHTS = 6


@dataclass(frozen=True)
class _Scored:
    score: int
    insight: Insight


def _ins(kind: InsightKind, tone: Tone, text: str, score: int) -> _Scored:
    return _Scored(score, Insight(kind=kind, tone=tone, text=text))


def join_names(names: list[str]) -> str:
    """["A"] -> "A"; ["A", "B"] -> "A y B"; ["A", "B", "C"] -> "A, B y C"."""
    if len(names) <= 1:
        return "".join(names)
    return f"{', '.join(names[:-1])} y {names[-1]}"


def _plural(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


# ---------- Reglas ----------
def _category_moves(r: MonthlyReport, prev_name: str) -> list[_Scored]:
    out: list[_Scored] = []
    ups = [
        c for c in r.expense_by_category
        if c.change_pct is not None and c.change_pct >= MIN_CHANGE_PCT and c.total - c.prev_total >= MIN_CHANGE_AMOUNT
    ]
    if ups:
        c = max(ups, key=lambda x: (x.total - x.prev_total, x.change_pct or 0.0))
        diff = c.total - c.prev_total
        out.append(_ins(
            InsightKind.CATEGORY_UP, Tone.WARNING,
            f"Gastaste {format_percent(c.change_pct or 0.0)} más en {c.name} que en {prev_name} "
            f"({format_cop(diff)} más).",
            90,
        ))
    downs = [
        c for c in r.expense_by_category
        if c.change_pct is not None and c.change_pct <= -MIN_CHANGE_PCT and c.prev_total - c.total >= MIN_CHANGE_AMOUNT
    ]
    if downs:
        c = max(downs, key=lambda x: (x.prev_total - x.total, -(x.change_pct or 0.0)))
        diff = c.prev_total - c.total
        if c.total == 0:
            text = f"No gastaste nada en {c.name} este mes (en {prev_name} fueron {format_cop(c.prev_total)})."
        else:
            text = (
                f"Gastaste {format_percent(abs(c.change_pct or 0.0))} menos en {c.name} que en {prev_name} "
                f"({format_cop(diff)} menos)."
            )
        out.append(_ins(InsightKind.CATEGORY_DOWN, Tone.POSITIVE, text, 70))
    return out


def _savings_record(r: MonthlyReport) -> list[_Scored]:
    previous = [t for t in r.trend[:-1] if t.income > 0 or t.expense > 0]
    net = r.summary.net
    if net <= 0 or not previous or any(t.net >= net for t in previous):
        return []
    return [_ins(
        InsightKind.SAVINGS_RECORD, Tone.POSITIVE,
        f"Ahorraste {format_cop(net)}: tu mejor mes de los últimos {len(r.trend)} meses.", 85,
    )]


def _new_income(r: MonthlyReport) -> list[_Scored]:
    if r.summary.prev.income <= 0:  # sin ingresos el mes anterior, todo sería "nuevo"
        return []
    new = [c for c in r.income_by_category if c.is_new]
    if not new:
        return []
    c = max(new, key=lambda x: x.total)
    return [_ins(
        InsightKind.NEW_INCOME, Tone.POSITIVE,
        f"Recibiste un ingreso nuevo por {c.name}: {format_cop(c.total)}.", 80,
    )]


def _budgets_exceeded(r: MonthlyReport) -> list[_Scored]:
    over = [(b, b.spent - b.amount_limit) for b in r.budgets if b.status == BudgetState.EXCEEDED]
    if not over:
        return []
    over.sort(key=lambda x: -x[1])
    name = lambda b: r.category_names.get(b.category_id, "Un presupuesto")  # noqa: E731
    if len(over) == 1:
        b, amount = over[0]
        text = f"{name(b)} superó su presupuesto por {format_cop(amount)}."
    else:
        total = sum((a for _, a in over), Decimal(0))
        names = [name(b) for b, _ in over]
        listed = names if len(names) <= MAX_NAMES_LISTED else [*names[:MAX_NAMES_LISTED], f"{len(names) - MAX_NAMES_LISTED} más"]
        text = (
            f"{len(over)} presupuestos se excedieron ({join_names(listed)}): "
            f"{format_cop(total)} por encima de lo planeado."
        )
    return [_ins(InsightKind.BUDGET_EXCEEDED, Tone.WARNING, text, 100)]


def _pay_periods(r: MonthlyReport) -> list[_Scored]:
    # los periodos de calendario no se juzgan: no se sabe cuál es el sueldo
    closed = [p for p in r.pay_periods if not p.in_progress and p.source == PeriodSource.PAYCHECK]
    out: list[_Scored] = []
    deficits = [p for p in closed if p.net < 0]
    if deficits:
        p = min(deficits, key=lambda x: x.net)
        out.append(_ins(
            InsightKind.PAY_PERIOD_SHORT, Tone.WARNING,
            f"Tu quincena del {short_date(p.start)} al {short_date(p.end)} cerró en déficit: "
            f"gastaste {format_cop(-p.net)} más de lo que recibiste.",
            95,
        ))
    elif len(closed) >= 2:
        shortest = min(closed, key=lambda x: (x.days, x.start))
        longest = max(closed, key=lambda x: (x.days, -x.start.toordinal()))
        if longest.days - shortest.days >= 2:
            out.append(_ins(
                InsightKind.PAY_PERIOD_SHORT, Tone.NEUTRAL,
                f"Tu quincena más corta fue del {short_date(shortest.start)} al {short_date(shortest.end)} "
                f"({shortest.days} días) y la más larga del {short_date(longest.start)} al "
                f"{short_date(longest.end)} ({longest.days} días).",
                45,
            ))
    return out


def _no_spend_days(r: MonthlyReport) -> list[_Scored]:
    n, total = r.daily_stats.no_spend_days, len(r.daily)
    month = month_name(r.month)
    if n == 0:
        return [_ins(InsightKind.NO_SPEND_DAYS, Tone.NEUTRAL,
                     f"Gastaste todos los días de {month}: ningún día sin gastos.", 40)]
    if n == total:
        return [_ins(InsightKind.NO_SPEND_DAYS, Tone.NEUTRAL,
                     f"No registraste gastos en ningún día de {month}.", 40)]
    tone, score = (Tone.POSITIVE, 55) if n >= 3 else (Tone.NEUTRAL, 40)
    return [_ins(InsightKind.NO_SPEND_DAYS, tone, f"Tuviste {_plural(n, 'día', 'días')} sin gastos en {month}.", score)]


def _savings_rate(r: MonthlyReport, prev_name: str) -> list[_Scored]:
    s = r.summary
    kind = InsightKind.SAVINGS_RATE
    if s.income <= 0:
        if s.expense > 0:
            return [_ins(kind, Tone.WARNING,
                         f"No registraste ingresos en {month_name(r.month)} y gastaste {format_cop(s.expense)}.", 75)]
        return [_ins(kind, Tone.NEUTRAL, f"Aún no hay movimientos en {month_name(r.month)}.", 30)]
    if s.net < 0:
        return [_ins(kind, Tone.WARNING,
                     f"Gastaste {format_cop(-s.net)} más de lo que recibiste: tu tasa de ahorro fue "
                     f"{format_percent1(s.savings_rate)}.", 98)]
    prev = f" ({prev_name}: {format_percent1(s.prev.savings_rate)})" if s.prev.income > 0 else ""
    if s.savings_rate >= SAVINGS_TARGET:
        return [_ins(kind, Tone.POSITIVE,
                     f"Tu tasa de ahorro fue {format_percent1(s.savings_rate)}: superas la meta sugerida "
                     f"del 20 %{prev}.", 60)]
    tone, score = (Tone.WARNING, 75) if s.savings_rate < 10 else (Tone.NEUTRAL, 65)
    return [_ins(kind, tone,
                 f"Tu tasa de ahorro fue {format_percent1(s.savings_rate)}, por debajo de la meta sugerida "
                 f"del 20 %{prev}.", score)]


def generate_insights(r: MonthlyReport) -> list[Insight]:
    """Entre 2 y 6 observaciones, de la más a la menos relevante."""
    prev_name = month_name(add_months(r.month, -1))
    rules: list[Callable[[], list[_Scored]]] = [
        lambda: _category_moves(r, prev_name),
        lambda: _savings_record(r),
        lambda: _new_income(r),
        lambda: _budgets_exceeded(r),
        lambda: _pay_periods(r),
        lambda: _no_spend_days(r),
        lambda: _savings_rate(r, prev_name),
    ]
    found = [item for rule in rules for item in rule()]
    found.sort(key=lambda x: -x.score)  # estable: a igual relevancia, el orden de las reglas
    return [x.insight for x in found[:MAX_INSIGHTS]]


# ---------- "Para el próximo mes" (página 3 del PDF) ----------
def next_month_outlook(r: MonthlyReport) -> str:
    """Texto de cierre: ahorro estimado si las 2 categorías que más subieron vuelven al nivel del mes
    anterior y aporte mensual que necesita la meta más atrasada; si no hay nada útil, una frase genérica."""
    prev_name = month_name(add_months(r.month, -1))
    s = r.summary
    sentences: list[str] = []

    if not r.is_partial:  # un mes parcial no es comparable con el anterior completo
        rises = [
            c for c in r.expense_by_category
            if c.change_pct is not None and c.change_pct >= MIN_CHANGE_PCT and c.total - c.prev_total >= MIN_CHANGE_AMOUNT
        ]
        rises.sort(key=lambda c: -(c.total - c.prev_total))
        top = rises[:2]
        if top:
            saving = sum((c.total - c.prev_total for c in top), Decimal(0))
            projected = s.net + saving
            held = join_names([f"{c.name} en {format_cop(c.prev_total)}" for c in top])
            if projected > 0:
                tail = f"ahorrarías cerca de {format_cop(projected)}"
                if s.income > 0:
                    tail += f" ({format_percent(float(projected / s.income * 100))})"
            else:
                tail = f"mejorarías tu balance en {format_cop(saving)}"
            sentences.append(f"Si mantienes {held} (como en {prev_name}), {tail}.")

    behind = [g for g in r.goals if g.status.value == "behind" and g.monthly_needed is not None and g.target_date]
    if behind:
        g = max(behind, key=lambda x: (x.monthly_needed or Decimal(0)) - x.contributed_this_month)
        assert g.monthly_needed is not None and g.target_date is not None
        sentences.append(
            f"Tu meta «{g.name}» necesita {format_cop(g.monthly_needed)} al mes para llegar a su fecha "
            f"objetivo ({month_name(g.target_date)} de {g.target_date.year})."
        )

    if sentences:
        return " ".join(sentences)
    if s.income > 0:
        return (
            f"Mantén tu tasa de ahorro por encima del 20 %: con tus ingresos de {month_name(r.month)} "
            f"serían al menos {format_cop(s.income * Decimal('0.2'))} al mes."
        )
    return "Registra tus ingresos y gastos del mes para recibir sugerencias personalizadas."
