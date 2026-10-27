"""Convierte un MonthlyReport en el contexto de la plantilla (textos ya formateados y SVG listos).

Sin dependencia de WeasyPrint: se puede probar en cualquier entorno."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from zoneinfo import ZoneInfo

from markupsafe import Markup

from app.domain.enums import BudgetState
from app.domain import formatting as fmt
from app.domain.formatting import MONTHS_SHORT_ES, long_date, month_name, month_year, short_date
from app.domain.monthly_report import CategoryChange, GoalReport, GoalStatus, InsightKind, MonthlyReport, Tone
from app.domain.pay_periods import PayPeriod, PeriodSource, PeriodStatus
from app.domain.rules import add_months
from app.infrastructure.reporting import charts

# Paleta por posición (design/DESIGN.md): la categoría más grande es naranja oscuro, luego verde marca...
SERIES_COLORS = ["#C2410C", "#0F5E55", "#B7791F", "#2563EB", "#6D28D9"]
OTHERS_COLOR = "#93A39B"
MAX_CATEGORY_ROWS = 6
MAX_PERIODS = 6
MAX_DENSITY = 3
LEGEND_NAME_CHARS = 15
# Alto del gráfico de 6 meses (página 1) según la densidad
TREND_HEIGHT = {0: 170, 1: 140, 2: 110, 3: 90}
INSIGHTS_SHOWN = {0: 6, 1: 6, 2: 5, 3: 4}
MAX_BUDGETS = 7
MAX_GOALS = 4
MAX_INCOME_SOURCES = 4

_INSIGHT_STYLE: dict[tuple[InsightKind, Tone] | InsightKind, tuple[str, str, str]] = {
    # (ícono, fondo, tinta)
    InsightKind.CATEGORY_UP: ("up", "#FFF4E8", "#C2410C"),
    InsightKind.CATEGORY_DOWN: ("down", "#E3F0ED", "#0F5E55"),
    InsightKind.SAVINGS_RECORD: ("star", "#E3F0ED", "#0F5E55"),
    InsightKind.NEW_INCOME: ("plus", "#E4ECFD", "#1D4ED8"),
    InsightKind.BUDGET_EXCEEDED: ("bang", "#FDECE2", "#B33A0A"),
    InsightKind.PAY_PERIOD_SHORT: ("bang", "#FFF4E8", "#C2410C"),
}
_TONE_STYLE = {
    Tone.POSITIVE: ("check", "#E3F0ED", "#0F5E55"),
    Tone.WARNING: ("bang", "#FFF4E8", "#C2410C"),
    Tone.NEUTRAL: ("dot", "#F4F6F3", "#55615B"),
}
_PERIOD_CHIP = {
    PeriodStatus.SAVING: ("ahorro", "#E3F0ED", "#0B4740"),
    PeriodStatus.TIGHT: ("justo", "#FFF0DC", "#8A4A0F"),
    PeriodStatus.IN_PROGRESS: ("en curso", "#E4ECFD", "#1E3A8A"),
    PeriodStatus.DEFICIT: ("déficit", "#FDE3D6", "#8A2C07"),
    PeriodStatus.CALENDAR: ("calendario", "#EEF1EE", "#55615B"),
}
_HEX = set("0123456789abcdefABCDEF")
NBSP = " "


def nb(text: str) -> str:
    """Espacio duro entre "$" y la cifra y antes de "%", para que un monto no se parta entre líneas."""
    return text.replace("$ ", "$" + NBSP).replace(" %", NBSP + "%")


def format_cop(v) -> str:
    return nb(fmt.format_cop(v))


def format_percent(v: float) -> str:
    return nb(fmt.format_percent(v))


def format_percent1(v: float) -> str:
    return nb(fmt.format_percent1(v))


def _ico(direction: str, color: str) -> Markup:
    name = {"up": "up", "new": "up", "down": "down"}.get(direction)
    return Markup(charts.icon(name, size=9, color=color) + " ") if name else Markup("")


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _f(d: Decimal) -> float:
    return float(d)


def _color(value: str, fallback: str = "#0F5E55") -> str:
    ok = len(value) == 7 and value[0] == "#" and all(c in _HEX for c in value[1:])
    return value if ok else fallback


def _short_month(month: str) -> str:
    return MONTHS_SHORT_ES[int(month[5:7]) - 1].capitalize()


def _delta(pct: float | None, prev_label: str, *, strong_round: bool = False) -> dict:
    """Variación para los KPI: {dir, text}. `pct` None = sin referencia."""
    if pct is None:
        return {"icon": "", "text": f"Sin datos de {prev_label}"}
    if round(pct, 1) == 0:
        return {"icon": "", "text": f"Igual que {prev_label}"}
    if abs(pct) >= 1000:
        shown = "más de 999" + NBSP + "%"
    else:
        shown = format_percent(abs(pct)) if strong_round else format_percent1(abs(pct))
    return {"icon": _ico("up" if pct > 0 else "down", "#FFFFFF"), "text": f"{shown} vs {prev_label}"}


def _span_label(start: date, end: date) -> str:
    if start.month == end.month and start.year == end.year:
        return f"{start.day} – {short_date(end)}"
    return f"{short_date(start)} – {short_date(end)}"


# ---------- Categorías (dona, barra apilada y tabla comparten agrupación y colores) ----------
def _group_categories(rows: list[CategoryChange]) -> list[dict]:
    rows = [r for r in rows if r.total > 0 or r.prev_total > 0]
    head, tail = (rows[:MAX_CATEGORY_ROWS], []) if len(rows) <= MAX_CATEGORY_ROWS else (
        rows[: MAX_CATEGORY_ROWS - 1], rows[MAX_CATEGORY_ROWS - 1:]
    )
    items = [
        {"name": r.name, "total": r.total, "prev": r.prev_total, "pct": r.percent, "pct_change": r.change_pct}
        for r in head
    ]
    if tail:
        total = sum((r.total for r in tail), Decimal(0))
        prev = sum((r.prev_total for r in tail), Decimal(0))
        items.append({
            "name": "Otros", "total": total, "prev": prev,
            "pct": round(sum(r.percent for r in tail), 1),
            "pct_change": round(float((total - prev) / prev * 100), 1) if prev else None,
        })
    out = []
    for i, it in enumerate(items):
        series = OTHERS_COLOR if (tail and i == len(items) - 1) else SERIES_COLORS[min(i, len(SERIES_COLORS) - 1)]
        pc = it["pct_change"]
        if pc is None:
            delta = {"icon": _ico("new", "#B33A0A"), "text": "Nuevo", "color": "#B33A0A"} if it["total"] > 0 else {"icon": "", "text": "—", "color": "#55615B"}
        elif round(pc) == 0:
            delta = {"icon": "", "text": nb("= 0 %"), "color": "#55615B"}
        else:  # más gasto = rojo; menos gasto = verde
            up = pc > 0
            color = "#B33A0A" if up else "#0F5E55"
            delta = {"icon": _ico("up" if up else "down", color), "text": format_percent(abs(pc)), "color": color}
        out.append({
            "name": it["name"], "color": series, "total": format_cop(it["total"]), "prev": format_cop(it["prev"]),
            "pct": format_percent(it["pct"]), "delta": delta, "value": _f(it["total"]),
        })
    return out


def _spent_vs_saved(r: MonthlyReport) -> dict:
    s = r.summary
    if s.income <= 0:
        return {"empty": True}
    spent = int(round(float(s.expense / s.income * 100)))
    return {"empty": False, "spent": spent, "saved": 100 - spent, "deficit": spent > 100}


def _period_card(p: PayPeriod) -> dict:
    label, bg, fg = _PERIOD_CHIP[p.status]
    ratio = p.spent_percent
    bar = "#B33A0A" if ratio > 100 else "#E58A2E" if ratio > 90 else "#0F5E55"
    if p.net >= 0:
        net, net_color = (f"{'Lleva' if p.in_progress else 'Sobraron'} {format_cop(p.net)}", "#0F5E55")
    else:
        net, net_color = (f"{'Va en déficit por' if p.in_progress else 'Faltaron'} {format_cop(-p.net)}", "#B33A0A")
    if p.extra_income > 0:
        received = [("Sueldo", format_cop(p.salary_income)), ("Extra", format_cop(p.extra_income))]
    else:
        received = [("Recibido", format_cop(p.income))]
    return {
        "label": _span_label(p.start, p.end), "status": label, "chip_bg": bg, "chip_fg": fg,
        "received": received,
        "income": format_cop(p.income), "expense": format_cop(p.expense),
        "per_day": format_cop(p.spent_per_day) if p.expense > 0 else "Sin gastos",
        "used": f"{min(100.0, ratio):.1f}", "bar": bar, "net": net, "net_color": net_color,
    }


def _goal_card(g: GoalReport) -> dict:
    left = g.target_amount - g.saved
    if g.status == GoalStatus.COMPLETED:
        state, color = "Meta cumplida", "#0F5E55"
    elif g.status == GoalStatus.BEHIND:
        extra = "sin aportes este mes" if g.contributed_this_month <= 0 else (
            f"aportaste {format_cop(g.contributed_this_month)} de {format_cop(g.monthly_needed or 0)} necesarios"
        )
        state, color = f"Atrasada: {extra}", "#B33A0A"
    elif g.percent >= 85:
        state, color = f"Casi: faltan {format_cop(left)}", "#0F5E55"
    elif g.status == GoalStatus.NO_TARGET_DATE:
        state, color = (
            (f"Aportaste {format_cop(g.contributed_this_month)} este mes", "#0F5E55")
            if g.contributed_this_month > 0 else ("Sin fecha objetivo", "#55615B")
        )
    else:
        state, color = (
            (f"Vas bien: aportaste {format_cop(g.contributed_this_month)}", "#0F5E55")
            if g.contributed_this_month > 0 else ("Vas bien", "#0F5E55")
        )
    return {
        "name": g.name,
        "progress": f"{format_cop(g.saved)} de {format_cop(g.target_amount)}",
        "state": state, "state_color": color,
        "ring": Markup(charts.goal_ring(g.percent, _color(g.color), aria=f"{g.name} {int(round(g.percent))} por ciento")),
    }


def _budget_rows(r: MonthlyReport) -> tuple[list[dict], int, str]:
    ordered = sorted(r.budgets, key=lambda b: (-b.percent, r.category_names.get(b.category_id, "")))
    shown, hidden = ordered[:MAX_BUDGETS], max(0, len(ordered) - MAX_BUDGETS)
    rows = []
    for b in shown:
        color = {BudgetState.EXCEEDED: "#B33A0A", BudgetState.WARNING: "#E58A2E"}.get(b.status, "#0F5E55")
        threshold = float(b.alert_threshold) * 100
        rows.append({
            "name": r.category_names.get(b.category_id, "Presupuesto"),
            "pct": nb(f"{int(round(b.percent))} %"),
            "detail": f"{format_cop(b.spent)} de {format_cop(b.amount_limit)}",
            "bar": Markup(charts.budget_bar(b.percent, threshold, color, width=290)),
        })
    thresholds = {round(float(b.alert_threshold) * 100) for b in r.budgets}
    note = (
        f"La línea gris marca el umbral de alerta ({thresholds.pop()} %)."
        if len(thresholds) == 1 else "La línea gris marca el umbral de alerta de cada presupuesto."
    )
    return rows, hidden, note


def _income_sources(r: MonthlyReport, prev_label: str) -> tuple[list[dict], int]:
    rows = [c for c in r.income_by_category if c.total > 0]
    shown, hidden = rows[:MAX_INCOME_SOURCES], max(0, len(rows) - MAX_INCOME_SOURCES)
    out = []
    for i, c in enumerate(shown):
        if c.is_new:
            sub = {"icon": _ico("new", "#1D4ED8"), "text": "Nuevo este mes", "color": "#1D4ED8", "bold": True}
        elif c.change_pct is None or round(c.change_pct, 1) == 0:
            sub = {"icon": "", "text": f"Igual que {prev_label}", "color": "#55615B", "bold": False}
        else:
            up = c.change_pct > 0
            color = "#1D4ED8" if up else "#55615B"
            sub = {"icon": _ico("up" if up else "down", color), "bold": False, "color": color,
                   "text": f"{format_percent(abs(c.change_pct))} vs {prev_label}"}
        out.append({
            "name": c.name, "total": format_cop(c.total), "width": f"{min(100.0, c.percent):.1f}",
            "color": "#1D4ED8" if i == 0 else "#60A5FA", "sub": sub,
        })
    return out, hidden


def _top_expenses(r: MonthlyReport) -> list[dict]:
    out = []
    for i, t in enumerate(r.top_expenses, start=1):
        title = (t.note or "").strip() or t.category or "Gasto"
        meta = " · ".join(x for x in (t.category, short_date(t.date)) if x)
        out.append({"rank": i, "note": title, "meta": meta, "amount": format_cop(t.amount)})
    return out


def _daily_facts(r: MonthlyReport) -> dict:
    ds = r.daily_stats
    peak = None
    if ds.max_day is not None:
        which = next((t for t in r.top_expenses if t.date == ds.max_day), None)
        what = (which.note or which.category) if which else None
        peak = {"when": f"{short_date(ds.max_day)} · {format_cop(ds.max_day_expense)}", "what": what}
    return {"peak": peak, "avg": format_cop(ds.avg_daily_expense), "no_spend": ds.no_spend_days}


def initial_density(r: MonthlyReport) -> int:
    """Densidad inicial de la página 1: 0 = diseño original; 1 = compacta si hay 5-6 observaciones o
    más de 3 quincenas. El renderer sube la densidad (hasta MAX_DENSITY) si aun así no cabe."""
    return 1 if len(r.insights) > 4 or len(r.pay_periods) > 3 else 0


def build_context(r: MonthlyReport, density: int | None = None) -> dict:
    density = initial_density(r) if density is None else max(0, min(density, MAX_DENSITY))
    prev_month = add_months(r.month, -1)
    prev_label = month_name(prev_month)
    cur_label = month_name(r.month)
    title = month_year(r.month)
    s = r.summary
    tz = ZoneInfo(r.timezone) if r.timezone else ZoneInfo("UTC")
    try:
        generated = r.generated_at.astimezone(tz).date()
    except Exception:  # zona inválida
        generated = r.generated_at.date()

    kpis = [
        {"label": "Ingresos", "value": format_cop(s.income), "delta": _delta(s.income_change_pct, prev_label)},
        {"label": "Gastos", "value": format_cop(s.expense), "delta": _delta(s.expense_change_pct, prev_label)},
        {"label": "Ahorro", "value": format_cop(s.net), "delta": _delta(s.net_change_pct, prev_label, strong_round=True)},
        {"label": "Tasa de ahorro", "value": format_percent1(s.savings_rate),
         "delta": {"icon": "", "text": f"{prev_label.capitalize()}: {format_percent1(s.prev.savings_rate)}"}
         if s.prev.income > 0 else {"icon": "", "text": f"Sin datos de {prev_label}"}},
    ]
    insights = []
    for i in r.insights[: INSIGHTS_SHOWN[density]]:
        icon, bg, ink = _INSIGHT_STYLE.get(i.kind) or _TONE_STYLE[i.tone]
        if i.kind in (InsightKind.NO_SPEND_DAYS, InsightKind.SAVINGS_RATE):
            icon, bg, ink = _TONE_STYLE[i.tone]
        insights.append({"icon": Markup(charts.icon(icon, size=11, color=ink)), "bg": bg, "ink": ink, "text": nb(i.text)})

    cats = _group_categories(r.expense_by_category)
    cat_segments = [(c["value"], c["color"]) for c in cats]
    budgets, budgets_hidden, budgets_note = _budget_rows(r)
    sources, sources_hidden = _income_sources(r, prev_label)

    trend = r.trend
    ctx = {
        "title": title,
        "month_lower": f"{cur_label} {r.month.year}",
        "kicker": "Reporte mensual" + (f" · parcial al {short_date(r.daily[-1].date)}" if r.is_partial and r.daily else ""),
        "generated": long_date(generated),
        "currency_note": "pesos colombianos (COP)" if r.currency == "COP" else r.currency,
        "kpis": kpis,
        "insights": insights,
        "cats": cats,
        "cur_label": cur_label.capitalize(),
        "prev_label": prev_label.capitalize(),
        "stacked": Markup(charts.stacked_bar(cat_segments, width=278, height=26)),
        "legend": [{"name": _clip(c["name"], LEGEND_NAME_CHARS), "color": c["color"], "pct": c["pct"]} for c in cats if c["value"] > 0],
        "spent_vs_saved": _spent_vs_saved(r),
        "periods": [_period_card(p) for p in (r.pay_periods[-3:] if density >= 3 else r.pay_periods[:MAX_PERIODS])],
        "density": density,
        "periods_note": "De un pago al siguiente"
        if not r.pay_periods or any(p.source == PeriodSource.PAYCHECK for p in r.pay_periods)
        else "Del 1 al 15 y del 16 a fin de mes",
        "trend_chart": Markup(charts.grouped_bars(
            [_short_month(t.month) for t in trend], [_f(t.income) for t in trend], [_f(t.expense) for t in trend],
            highlight=len(trend) - 1, height=TREND_HEIGHT[density],
        )),
        "donut": Markup(charts.donut(cat_segments, size=180, aria="Distribución de gastos por categoría")),
        "top_expenses": _top_expenses(r),
        "sources": sources,
        "sources_hidden": sources_hidden,
        "daily_chart": Markup(charts.daily_bars(
            [_f(d.expense) for d in r.daily], [d.is_payday for d in r.daily], [d.date.day for d in r.daily],
            columns=_days_in_month(r.month),
        )),
        "daily_facts": _daily_facts(r),
        "budgets": budgets,
        "budgets_hidden": budgets_hidden,
        "budgets_note": budgets_note,
        "budget_chips": _budget_chips(r),
        "goals": [_goal_card(g) for g in r.goals[:MAX_GOALS]],
        "goals_hidden": max(0, len(r.goals) - MAX_GOALS),
        "rate_chart": Markup(charts.savings_line([t.savings_rate for t in trend])),
        "rate_labels": [{"label": _short_month(t.month), "value": format_percent1(t.savings_rate)} for t in trend],
        "outlook_title": f"Para {month_name(add_months(r.month, 1))}",
        "outlook": nb(r.outlook),
    }
    return ctx


def _days_in_month(month: date) -> int:
    return (add_months(month, 1) - month).days


def _budget_chips(r: MonthlyReport) -> list[dict]:
    b = r.budgets_summary
    chips = []
    if b.ok:
        chips.append({"text": f"{b.ok} cumplido{'s' if b.ok != 1 else ''}", "bg": "#E3F0ED", "fg": "#0B4740"})
    if b.warning:
        chips.append({"text": f"{b.warning} en riesgo", "bg": "#FFF0DC", "fg": "#8A4A0F"})
    if b.exceeded:
        chips.append({"text": f"{b.exceeded} excedido{'s' if b.exceeded != 1 else ''}", "bg": "#FDE3D6", "fg": "#8A2C07"})
    return chips
