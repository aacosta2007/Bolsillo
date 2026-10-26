"""Reglas de observaciones, métricas del reporte mensual, gráficas SVG y plantilla (sin BD ni WeasyPrint)."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.domain.entities import CategoryTotal, DailyTotal
from app.domain.formatting import format_percent1, long_date, month_year
from app.domain.insights import (
    MAX_INSIGHTS,
    MIN_INSIGHTS,
    generate_insights,
    join_names,
    next_month_outlook,
)
from app.domain.monthly_report import (
    GoalStatus,
    InsightKind,
    Tone,
    build_category_changes,
    build_daily,
    build_summary,
    change_pct,
    goal_status,
    savings_rate,
)
from app.infrastructure.reporting import charts
from app.infrastructure.reporting.sample import sample_report
from app.infrastructure.reporting.viewmodel import build_context
from tests.unit.report_builders import MONTH, budget, cid, goal, make_report, period

D = Decimal


def kinds(report) -> list[InsightKind]:
    return [i.kind for i in generate_insights(report)]


def one(report, kind: InsightKind):
    found = [i for i in generate_insights(report) if i.kind == kind]
    assert len(found) == 1, f"{kind}: {[i.kind for i in generate_insights(report)]}"
    return found[0]


# ---------- Métricas ----------
def test_change_pct_with_zero_previous_is_none_and_rounds_to_one_decimal():
    assert change_pct(D(100), D(0)) is None
    assert change_pct(D(0), D(0)) is None
    assert change_pct(D(2350000), D(2000000)) == 17.5
    assert change_pct(D(0), D(50000)) == -100.0
    assert change_pct(D(665700), D(410000)) == 62.4
    assert change_pct(D(100), D(-100)) == 200.0  # base negativa: el signo del cambio sigue siendo intuitivo


def test_savings_rate():
    assert savings_rate(D(2350000), D(1684300)) == 28.3
    assert savings_rate(D(0), D(500)) == 0.0
    assert savings_rate(D(100), D(150)) == -50.0


def test_summary_matches_contract_example():
    s = build_summary(D(2350000), D(1684300), D(2000000), D(1590000))
    assert (s.net, s.savings_rate) == (D(665700), 28.3)
    assert (s.prev.net, s.prev.savings_rate) == (D(410000), 20.5)
    assert (s.income_change_pct, s.expense_change_pct, s.net_change_pct) == (17.5, 5.9, 62.4)


def test_summary_without_previous_month_has_null_changes():
    s = build_summary(D(1000), D(400), D(0), D(0))
    assert s.income_change_pct is None and s.expense_change_pct is None and s.net_change_pct is None


def test_category_changes_include_dropped_to_zero_and_new_income():
    cur = [CategoryTotal(category_id=cid("A"), name="A", color="#111111", icon="x", total=D(300), count=3)]
    prev = [
        CategoryTotal(category_id=cid("A"), name="A", color="#111111", icon="x", total=D(200), count=1),
        CategoryTotal(category_id=cid("B"), name="B", color="#222222", icon="y", total=D(500), count=2),
    ]
    rows = build_category_changes(cur, prev)
    assert [r.name for r in rows] == ["A", "B"]  # total desc
    a, b = rows
    assert (a.total, a.prev_total, a.change_pct, a.percent, a.count) == (D(300), D(200), 50.0, 100.0, 3)
    assert (b.total, b.prev_total, b.change_pct, b.percent, b.count) == (D(0), D(500), -100.0, 0.0, 0)

    inc = build_category_changes(
        [CategoryTotal(category_id=cid("S"), name="Salario", color="#1", icon="x", total=D(900), count=1),
         CategoryTotal(category_id=cid("F"), name="Freelance", color="#2", icon="y", total=D(100), count=1)],
        [CategoryTotal(category_id=cid("S"), name="Salario", color="#1", icon="x", total=D(900), count=1)],
        flag_new=True,
    )
    by = {r.name: r for r in inc}
    assert by["Freelance"].is_new and by["Freelance"].change_pct is None
    assert not by["Salario"].is_new and by["Salario"].change_pct == 0.0
    assert by["Freelance"].percent == 10.0


def test_daily_series_stats_and_paydays():
    rows = [
        DailyTotal(date=date(2026, 10, 2), income=D(0), expense=D(30), paycheck_income=D(0)),
        DailyTotal(date=date(2026, 10, 3), income=D(500), expense=D(10), paycheck_income=D(500)),
    ]
    days, stats = build_daily(date(2026, 10, 1), date(2026, 10, 5), rows)
    assert [d.date.day for d in days] == [1, 2, 3, 4, 5]
    assert [d.is_payday for d in days] == [False, False, True, False, False]
    assert stats.max_day == date(2026, 10, 2) and stats.max_day_expense == D(30)
    assert stats.avg_daily_expense == D("8.00")  # 40 / 5 días considerados
    assert stats.no_spend_days == 3
    empty, empty_stats = build_daily(date(2026, 10, 1), date(2026, 10, 2), [])
    assert empty_stats.max_day is None and empty_stats.no_spend_days == 2 and len(empty) == 2


def test_goal_status_rules():
    kw = dict(target_amount=D(1000), target_date=date(2027, 1, 1))
    assert goal_status(saved=D(1000), monthly_needed=None, contributed_this_month=D(0), **kw) == GoalStatus.COMPLETED
    assert goal_status(saved=D(10), monthly_needed=None, contributed_this_month=D(0),
                       target_amount=D(1000), target_date=None) == GoalStatus.NO_TARGET_DATE
    assert goal_status(saved=D(10), monthly_needed=D(100), contributed_this_month=D(100), **kw) == GoalStatus.ON_TRACK
    assert goal_status(saved=D(10), monthly_needed=D(100), contributed_this_month=D(99), **kw) == GoalStatus.BEHIND
    # completada gana sobre "sin fecha"
    assert goal_status(saved=D(1000), monthly_needed=None, contributed_this_month=D(0),
                       target_amount=D(1000), target_date=None) == GoalStatus.COMPLETED


# ---------- Reglas de observaciones ----------
@pytest.mark.parametrize(
    "total, prev, expected",
    [
        (1000000, 800000, True),  # 25 % y $ 200.000
        (220000, 200000, True),  # 10 % y $ 20.000: justo en los dos umbrales
        (219999, 200000, False),  # < $ 20.000
        (1999999, 1000000 + 900000, False),  # +5 %: no llega al 10 %
        (1090000, 1000000, False),  # 9 % aunque son $ 90.000
        (300000, 0, False),  # sin mes anterior no hay variación
    ],
)
def test_category_up_thresholds(total, prev, expected):
    r = make_report(expense=total, prev_expense=prev, expense_cats=[("Comida", total, prev)])
    assert (InsightKind.CATEGORY_UP in kinds(r)) is expected


def test_category_up_text_and_picks_largest_peso_increase():
    r = make_report(
        expense=1500000, prev_expense=1100000,
        expense_cats=[("Comida", 452300, 383300), ("Ocio", 300000, 100000), ("Hogar", 747700, 616700)],
    )
    i = one(r, InsightKind.CATEGORY_UP)
    assert i.tone == Tone.WARNING
    assert i.text == "Gastaste 200 % más en Ocio que en septiembre ($ 200.000 más)."
    r2 = make_report(expense=835300, prev_expense=766300, expense_cats=[("Comida", 452300, 383300), ("Hogar", 383000, 383000)])
    assert one(r2, InsightKind.CATEGORY_UP).text == "Gastaste 18 % más en Comida que en septiembre ($ 69.000 más)."


@pytest.mark.parametrize(
    "total, prev, expected",
    [(300000, 400000, True), (180000, 200000, True), (180001, 200000, False), (950000, 1000000, False)],
)
def test_category_down_thresholds(total, prev, expected):
    r = make_report(expense=total, prev_expense=prev, expense_cats=[("Servicios", total, prev)])
    assert (InsightKind.CATEGORY_DOWN in kinds(r)) is expected


def test_category_down_to_zero_has_its_own_text():
    r = make_report(expense=500000, prev_expense=600000, expense_cats=[("Comida", 500000, 500000), ("Gym", 0, 100000)])
    i = one(r, InsightKind.CATEGORY_DOWN)
    assert i.tone == Tone.POSITIVE
    assert i.text == "No gastaste nada en Gym este mes (en septiembre fueron $ 100.000)."


def test_savings_record_requires_best_net_of_trend():
    best = make_report(income=3000000, expense=1000000, prior_trend=[(2000000, 1500000)] * 4)
    assert one(best, InsightKind.SAVINGS_RECORD).text == "Ahorraste $ 2.000.000: tu mejor mes de los últimos 6 meses."
    # un mes anterior igual o mejor: no es récord
    tie = make_report(income=3000000, expense=1000000, prior_trend=[(2000000, 1500000), (3000000, 1000000), (2000000, 1500000), (2000000, 1500000)])
    assert InsightKind.SAVINGS_RECORD not in kinds(tie)
    beaten = make_report(income=3000000, expense=1000000, prior_trend=[(5000000, 1000000)] + [(2000000, 1500000)] * 3)
    assert InsightKind.SAVINGS_RECORD not in kinds(beaten)
    # sin ahorro no hay récord, y sin historia previa tampoco
    assert InsightKind.SAVINGS_RECORD not in kinds(make_report(income=1000000, expense=1200000))
    nohist = make_report(income=3000000, expense=1000000, prev_income=0, prev_expense=0, prior_trend=[(0, 0)] * 4)
    assert InsightKind.SAVINGS_RECORD not in kinds(nohist)


def test_new_income_needs_previous_income_and_a_new_source():
    r = make_report(
        income=2350000, prev_income=2000000,
        income_cats=[("Salario", 2000000, 2000000), ("Freelance", 350000, 0), ("Regalo", 100000, 0)],
    )
    i = one(r, InsightKind.NEW_INCOME)
    assert i.tone == Tone.POSITIVE and i.text == "Recibiste un ingreso nuevo por Freelance: $ 350.000."
    same = make_report(income=2000000, prev_income=2000000, income_cats=[("Salario", 2000000, 2000000)])
    assert InsightKind.NEW_INCOME not in kinds(same)
    first_month = make_report(income=2000000, prev_income=0, income_cats=[("Salario", 2000000, 0)])
    assert InsightKind.NEW_INCOME not in kinds(first_month)  # todo sería "nuevo": no es noticia


def test_budget_exceeded_single_and_multiple():
    single = make_report(budgets=[budget("Entretenimiento", 120000, 100000), budget("Comida", 90000, 100000)])
    i = one(single, InsightKind.BUDGET_EXCEEDED)
    assert i.tone == Tone.WARNING and i.text == "Entretenimiento superó su presupuesto por $ 20.000."
    several = make_report(budgets=[budget("A", 150000, 100000), budget("B", 120000, 100000), budget("C", 50000, 100000)])
    assert one(several, InsightKind.BUDGET_EXCEEDED).text == "2 presupuestos se excedieron (A y B): $ 70.000 por encima de lo planeado."
    many = make_report(budgets=[budget(n, 150000, 100000) for n in "ABCDE"])
    assert one(many, InsightKind.BUDGET_EXCEEDED).text == (
        "5 presupuestos se excedieron (A, B, C y 2 más): $ 250.000 por encima de lo planeado."
    )
    # exactamente el límite no es "excedido"
    assert InsightKind.BUDGET_EXCEEDED not in kinds(make_report(budgets=[budget("A", 100000, 100000)]))


def test_pay_period_deficit_and_length_difference():
    deficit = make_report(periods=[
        period(date(2026, 9, 30), date(2026, 10, 14), 1000000, 1200000),
        period(date(2026, 10, 15), date(2026, 10, 29), 1000000, 600000),
    ])
    i = one(deficit, InsightKind.PAY_PERIOD_SHORT)
    assert i.tone == Tone.WARNING
    assert i.text == "Tu quincena del 30 sep al 14 oct cerró en déficit: gastaste $ 200.000 más de lo que recibiste."
    uneven = make_report(periods=[
        period(date(2026, 9, 30), date(2026, 10, 12), 1000000, 600000),  # 13 días
        period(date(2026, 10, 13), date(2026, 10, 29), 1000000, 600000),  # 17 días
    ])
    j = one(uneven, InsightKind.PAY_PERIOD_SHORT)
    assert j.tone == Tone.NEUTRAL and "13 días" in j.text and "17 días" in j.text
    even = make_report(periods=[
        period(date(2026, 9, 30), date(2026, 10, 14), 1000000, 600000),
        period(date(2026, 10, 15), date(2026, 10, 29), 1000000, 600000),
    ])
    assert InsightKind.PAY_PERIOD_SHORT not in kinds(even)
    # una quincena en curso no cuenta como déficit
    ongoing = make_report(periods=[period(date(2026, 10, 15), date(2026, 11, 14), 1000, 5000, today=date(2026, 10, 20))])
    assert InsightKind.PAY_PERIOD_SHORT not in kinds(ongoing)


def test_no_spend_days_texts():
    four = make_report(spend_days=[d for d in range(1, 32) if d not in (3, 11, 19, 27)])
    i = one(four, InsightKind.NO_SPEND_DAYS)
    assert i.tone == Tone.POSITIVE and i.text == "Tuviste 4 días sin gastos en octubre."
    one_day = make_report(spend_days=[d for d in range(1, 32) if d != 7])
    assert one(one_day, InsightKind.NO_SPEND_DAYS).text == "Tuviste 1 día sin gastos en octubre."
    assert one(one_day, InsightKind.NO_SPEND_DAYS).tone == Tone.NEUTRAL
    assert one(make_report(), InsightKind.NO_SPEND_DAYS).text == "Gastaste todos los días de octubre: ningún día sin gastos."
    assert one(make_report(spend_days=[]), InsightKind.NO_SPEND_DAYS).text == "No registraste gastos en ningún día de octubre."


def test_savings_rate_rule_variants():
    above = one(make_report(income=2350000, expense=1684300, prev_income=2000000, prev_expense=1590000), InsightKind.SAVINGS_RATE)
    assert above.tone == Tone.POSITIVE
    assert above.text == "Tu tasa de ahorro fue 28,3 %: superas la meta sugerida del 20 % (septiembre: 20,5 %)."
    exactly = one(make_report(income=1000000, expense=800000), InsightKind.SAVINGS_RATE)
    assert exactly.tone == Tone.POSITIVE  # 20 % cuenta como meta cumplida
    below = one(make_report(income=1000000, expense=850000), InsightKind.SAVINGS_RATE)
    assert below.tone == Tone.NEUTRAL and "por debajo de la meta sugerida del 20 %" in below.text
    low = one(make_report(income=1000000, expense=950000), InsightKind.SAVINGS_RATE)
    assert low.tone == Tone.WARNING
    negative = one(make_report(income=1000000, expense=1200000), InsightKind.SAVINGS_RATE)
    assert negative.tone == Tone.WARNING and negative.text.startswith("Gastaste $ 200.000 más de lo que recibiste")
    no_income = one(make_report(income=0, expense=300000, prev_income=0, income_cats=[]), InsightKind.SAVINGS_RATE)
    assert "No registraste ingresos en octubre" in no_income.text
    nothing = one(make_report(income=0, expense=0, prev_income=0, prev_expense=0, expense_cats=[], income_cats=[]), InsightKind.SAVINGS_RATE)
    assert nothing.tone == Tone.NEUTRAL


def test_insights_are_between_two_and_six_and_sorted_by_relevance():
    quiet = generate_insights(make_report())
    assert MIN_INSIGHTS <= len(quiet) <= MAX_INSIGHTS
    empty = generate_insights(make_report(income=0, expense=0, prev_income=0, prev_expense=0, expense_cats=[], income_cats=[], spend_days=[]))
    assert len(empty) >= MIN_INSIGHTS

    busy = make_report(
        income=2350000, expense=1684300, prev_income=2000000, prev_expense=1590000,
        expense_cats=[("Comida", 452300, 383300), ("Servicios", 100000, 200000), ("Entretenimiento", 120000, 100000)],
        income_cats=[("Salario", 2000000, 2000000), ("Freelance", 350000, 0)],
        budgets=[budget("Entretenimiento", 120000, 100000)],
        periods=[period(date(2026, 9, 30), date(2026, 10, 14), 1000000, 1200000)],
        prior_trend=[(2000000, 1800000)] * 4,
        spend_days=[d for d in range(1, 32) if d not in (3, 11, 19, 27)],
    )
    got = generate_insights(busy)
    assert len(got) == MAX_INSIGHTS  # hay 8 candidatas; se queda con las 6 más relevantes
    assert got[0].kind == InsightKind.BUDGET_EXCEEDED
    assert got[1].kind == InsightKind.PAY_PERIOD_SHORT
    assert got[2].kind == InsightKind.CATEGORY_UP
    assert InsightKind.NO_SPEND_DAYS not in [i.kind for i in got]  # la menos relevante queda fuera
    assert all(i.text.endswith(".") for i in got)


# ---------- "Para el próximo mes" ----------
def test_outlook_cuts_the_two_biggest_risers_back_to_last_month_level():
    r = make_report(
        income=2350000, expense=1684300, prev_income=2000000, prev_expense=1590000,
        expense_cats=[("Hogar", 700000, 700000), ("Comida", 452300, 383300), ("Entretenimiento", 120000, 96000), ("Otros", 70000, 55700)],
    )
    text = next_month_outlook(r)
    # ahorro estimado = 665.700 + (69.000 + 24.000) = 758.700 -> 32 % de 2.350.000
    assert text == "Si mantienes Comida en $ 383.300 y Entretenimiento en $ 96.000 (como en septiembre), ahorrarías cerca de $ 758.700 (32 %)."


def test_outlook_only_one_riser_and_negative_projection():
    r = make_report(expense=1100000, prev_expense=1000000, income=1000000, prev_income=1000000,
                    expense_cats=[("Comida", 1100000, 1000000)])
    assert next_month_outlook(r) == "Si mantienes Comida en $ 1.000.000 (como en septiembre), mejorarías tu balance en $ 100.000."


def test_outlook_goal_behind_sentence_and_generic_fallbacks():
    behind = goal("Fondo de emergencia", saved=2400000, target=6000000, contributed=0, needed=300000, target_date=date(2027, 12, 1))
    r = make_report(goals=[behind, goal("Otra", saved=0, contributed=500000, needed=100000)])
    assert next_month_outlook(r) == (
        "Tu meta «Fondo de emergencia» necesita $ 300.000 al mes para llegar a su fecha objetivo (diciembre de 2027)."
    )
    generic = next_month_outlook(make_report(income=2000000))
    assert generic == "Mantén tu tasa de ahorro por encima del 20 %: con tus ingresos de octubre serían al menos $ 400.000 al mes."
    assert "Registra tus ingresos" in next_month_outlook(make_report(income=0, expense=0, prev_income=0, prev_expense=0, expense_cats=[], income_cats=[]))


def test_outlook_ignores_comparison_for_partial_month():
    r = make_report(
        is_partial=True, income=1000000, expense=900000, prev_income=1000000, prev_expense=500000,
        expense_cats=[("Comida", 900000, 500000)],
    )
    assert "Si mantienes" not in next_month_outlook(r)


def test_sample_report_matches_design_numbers():
    r = sample_report()
    assert MIN_INSIGHTS <= len(r.insights) <= MAX_INSIGHTS
    assert [i.kind for i in r.insights][:2] == [InsightKind.BUDGET_EXCEEDED, InsightKind.CATEGORY_UP]
    assert r.budgets_summary.ok == 3 and r.budgets_summary.warning == 1 and r.budgets_summary.exceeded == 1
    assert r.daily_stats.no_spend_days == 4 and r.daily_stats.max_day == date(2026, 10, 5)
    assert [g.status for g in r.goals] == [GoalStatus.ON_TRACK, GoalStatus.BEHIND, GoalStatus.BEHIND]


# ---------- Formato ----------
def test_formatting_helpers():
    assert format_percent1(17.5) == "17,5 %" and format_percent1(62.0) == "62 %" and format_percent1(-1.0) == "-1 %"
    assert long_date(date(2026, 11, 1)) == "1 de noviembre de 2026"
    assert month_year(date(2026, 10, 1)) == "Octubre 2026"
    assert join_names(["A"]) == "A" and join_names(["A", "B"]) == "A y B" and join_names(["A", "B", "C"]) == "A, B y C"


# ---------- Gráficas SVG ----------
def _parse(svg: str) -> ET.Element:
    root = ET.fromstring(svg)  # lanza ParseError si no está bien formado
    assert root.tag.endswith("svg")
    return root


@pytest.mark.parametrize(
    "svg",
    [
        charts.donut([(700, "#C2410C"), (452, "#0F5E55"), (0, "#000000")]),
        charts.donut([]),
        charts.donut([(1, "#C2410C")]),
        charts.stacked_bar([(41.6, "#C2410C"), (26.9, "#0F5E55")]),
        charts.stacked_bar([]),
        charts.grouped_bars(["May", "Jun", "Jul"], [2e6, 0, 3e6], [1.5e6, 1e6, 0], highlight=2),
        charts.grouped_bars(["May"], [0], [0]),
        charts.daily_bars([0, 50, 715, 10], [False, True, False, False], [1, 2, 3, 4], columns=31),
        charts.daily_bars([], [], []),
        charts.daily_bars([0.0, 0.0], [False, False], [1, 2]),
        charts.savings_line([12.5, 9, 23.8, -1, 20.5, 28.3]),
        charts.savings_line([5.0]),
        charts.savings_line([]),
        charts.goal_ring(35, "#0F5E55", aria='Meta "Viaje" <35>'),
        charts.goal_ring(0, "#0F5E55"),
        charts.goal_ring(140, "#0F5E55"),
        charts.budget_bar(85, 80, "#E58A2E"),
        charts.budget_bar(250, 80, "#B33A0A"),
        charts.budget_bar(0, 80, "#0F5E55"),
        charts.icon("star"),
        charts.icon("desconocido"),
    ],
)
def test_svg_helpers_return_valid_svg(svg):
    root = _parse(svg)
    assert root.get("width") and root.get("height") and root.get("viewBox")


def test_donut_arcs_cover_full_circle():
    root = _parse(charts.donut([(1, "#aaaaaa"), (1, "#bbbbbb")]))
    ns = "{http://www.w3.org/2000/svg}"
    arcs = [c for c in root.iter(f"{ns}circle") if c.get("stroke") in ("#aaaaaa", "#bbbbbb")]
    lengths = [float(c.get("stroke-dasharray").split()[0]) for c in arcs]
    assert len(arcs) == 2 and sum(lengths) == pytest.approx(2 * 3.14159265 * 38, rel=1e-3)


def test_chart_text_is_escaped():
    svg = charts.grouped_bars(["A&B", "<x>"], [1, 2], [2, 1])
    _parse(svg)
    assert "&amp;" in svg and "<x>" not in svg


# ---------- Plantilla (contexto + Jinja, sin WeasyPrint) ----------
def render_html(report) -> str:
    pytest.importorskip("jinja2")
    from app.infrastructure.reporting.weasy_renderer import WeasyReportRenderer

    return WeasyReportRenderer().render_html(report)


def test_context_formats_design_values():
    ctx = build_context(sample_report())
    assert ctx["title"] == "Octubre 2026" and ctx["generated"] == "1 de noviembre de 2026"
    assert [k["label"] for k in ctx["kpis"]] == ["Ingresos", "Gastos", "Ahorro", "Tasa de ahorro"]
    assert ctx["kpis"][0]["value"] == "$ 2.350.000" and ctx["kpis"][0]["delta"]["text"] == "17,5 % vs septiembre"
    assert ctx["kpis"][3]["value"] == "28,3 %" and ctx["kpis"][3]["delta"]["text"] == "Septiembre: 20,5 %"
    assert [c["name"] for c in ctx["cats"]] == ["Hogar/Arriendo", "Comida", "Servicios", "Transporte", "Entretenimiento", "Otros"]
    assert ctx["spent_vs_saved"] == {"empty": False, "spent": 72, "saved": 28, "deficit": False}
    assert [p["label"] for p in ctx["periods"]] == ["30 sep – 14 oct", "15 – 29 oct", "30 oct – 14 nov"]
    assert [p["status"] for p in ctx["periods"]] == ["justo", "ahorro", "en curso"]
    assert ctx["outlook_title"] == "Para noviembre"
    assert [c["text"] for c in ctx["budget_chips"]] == ["3 cumplidos", "1 en riesgo", "1 excedido"]


def test_template_renders_three_pages_with_footers():
    html = render_html(sample_report())
    assert html.count('<section class="page') == 3
    for n in (1, 2, 3):
        assert f"Página {n} de 3" in html
    assert "Bolsillo · Reporte de octubre 2026" in html
    for svg_part in ("<svg", "stroke-dasharray", "polyline"):
        assert svg_part in html
    assert "fonts/Figtree-400.ttf" in html and "size: A4" in html


def test_template_renders_empty_and_extreme_reports_without_errors():
    empty = make_report(income=0, expense=0, prev_income=0, prev_expense=0, expense_cats=[], income_cats=[], spend_days=[])
    html = render_html(empty)
    assert "No registraste gastos" in html and "No definiste presupuestos" in html and "Aún no tienes metas" in html
    many = make_report(
        income=5000000, expense=6000000, prev_income=5000000, prev_expense=1000000,
        expense_cats=[(f"Categoría {i}", 1000000 - i * 10000, 100000) for i in range(12)],
        income_cats=[(f"Fuente {i}", 100000 + i, 0 if i % 2 else 100000) for i in range(7)],
        budgets=[budget(f"Presupuesto {i}", 100000 * i, 200000) for i in range(11)],
        goals=[goal(f"Meta {i}") for i in range(6)],
        periods=[period(date(2026, 10, 1) + timedelta(days=k), date(2026, 10, 1) + timedelta(days=k + 6), 100000, 90000) for k in (0, 7, 14, 21, 28)],
    )
    html = render_html(many)
    assert "Otros" in html and "y 4 presupuestos más" in html and "y 2 metas más" in html and "y 3 fuentes más" in html
