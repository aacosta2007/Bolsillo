"""Reporte mensual (JSON y PDF) contra MariaDB real con datos de dos meses."""
from __future__ import annotations

import calendar
import io
from datetime import date, timedelta

import pytest
import pytest_asyncio

from app.domain.formatting import month_name
from app.domain.rules import add_months, first_of_month, last_of_month
from tests.integration.conftest import login, make_user
from tests.integration.test_api import TODAY, V1, mk_account
from tests.pdf_support import requires_weasyprint

R = f"{V1}/reports/monthly"
CUR = add_months(first_of_month(TODAY), -1)  # mes completo anterior al actual (el "octubre" del contrato)
PREV = add_months(CUR, -1)  # el mes anterior a ese (el "septiembre")
CUR_END = last_of_month(CUR)
DIM = calendar.monthrange(CUR.year, CUR.month)[1]
MONTH = CUR.strftime("%Y-%m")
PREV_MONTH_NAME = month_name(PREV)


def day(month: date, d: int) -> str:
    return month.replace(day=d).isoformat()


async def add_tx(api, account, category, amount, when: str, note: str | None = None, type="expense"):
    r = await api.post(f"{V1}/transactions", json={
        "type": type, "amount": str(amount), "date": when, "account_id": account["id"],
        "category_id": category["id"], "note": note,
    })
    assert r.status_code == 201, r.text
    return r.json()


@pytest_asyncio.fixture
async def data(api, cats):
    """Dos meses de datos: sueldo quincenal (regla is_paycheck) + gastos, ingreso nuevo, presupuestos y una meta."""
    acc = await mk_account(api, "Bancolombia")
    rule = await api.post(f"{V1}/recurring", json={
        "type": "income", "amount": "1000000", "account_id": acc["id"], "category_id": cats["Salario"]["id"],
        "note": "Sueldo", "frequency": "monthly_days", "days_of_month": "15,L",
        "start_date": PREV.isoformat(), "is_paycheck": True,
    })
    assert rule.status_code == 201, rule.text
    assert (await api.post(f"{V1}/recurring/run")).status_code == 200  # genera los sueldos hasta hoy

    # --- mes anterior ("septiembre") ---
    await add_tx(api, acc, cats["Hogar/Arriendo"], 700000, day(PREV, 5), "Arriendo")
    await add_tx(api, acc, cats["Comida"], 200000, day(PREV, 10), "Mercado")
    await add_tx(api, acc, cats["Comida"], 183300, day(PREV, 20), "Domicilios")
    await add_tx(api, acc, cats["Servicios"], 195000, day(PREV, 22), "Luz y agua")
    await add_tx(api, acc, cats["Salud"], 100000, day(PREV, 25), "Odontología")  # bajará a 0 el mes siguiente
    # --- mes del reporte ("octubre") ---
    await add_tx(api, acc, cats["Hogar/Arriendo"], 700000, day(CUR, 5), "Arriendo")
    await add_tx(api, acc, cats["Comida"], 150000, day(CUR, 8), "Mercado")
    await add_tx(api, acc, cats["Comida"], 200000, day(CUR, 12), "Mercado grande")
    await add_tx(api, acc, cats["Comida"], 102300, day(CUR, 18), "Domicilios")
    await add_tx(api, acc, cats["Servicios"], 182000, day(CUR, 20), "Plan celular")
    await add_tx(api, acc, cats["Entretenimiento"], 120000, day(CUR, 24), "Concierto")
    await add_tx(api, acc, cats["Freelance"], 350000, day(CUR, 9), "Proyecto web", type="income")  # fuente nueva
    other = await mk_account(api, "Nequi")  # una transferencia no cuenta como ingreso ni gasto
    tr = await api.post(f"{V1}/transactions", json={
        "type": "transfer", "amount": "999000", "date": day(CUR, 6), "account_id": acc["id"],
        "transfer_account_id": other["id"],
    })
    assert tr.status_code == 201, tr.text

    for name, limit in (("Entretenimiento", "100000"), ("Comida", "600000"), ("Hogar/Arriendo", "750000")):
        r = await api.post(f"{V1}/budgets", json={"category_id": cats[name]["id"], "month": MONTH, "amount_limit": limit})
        assert r.status_code == 201, r.text

    target = date(CUR_END.year + 1, CUR_END.month, 1)
    g = (await api.post(f"{V1}/goals", json={
        "name": "Viaje a Cartagena", "target_amount": "3000000", "target_date": target.isoformat(),
    })).json()
    for amount, when in (("200000", day(PREV, 3)), ("300000", day(CUR, 14)), ("100000", TODAY.isoformat())):
        r = await api.post(f"{V1}/goals/{g['id']}/contributions", json={"amount": amount, "date": when})
        assert r.status_code == 201, r.text
    return {"account": acc, "goal": g, "cats": cats}


async def get_report(api, month=MONTH):
    r = await api.get(f"{R}/{month}")
    assert r.status_code == 200, r.text
    return r.json()


# ---------------- JSON ----------------
async def test_full_report_matches_contract(api, data):
    rep = await get_report(api)
    assert set(rep) == {
        "month", "is_partial", "generated_at", "currency", "summary", "expense_by_category",
        "income_by_category", "top_expenses", "daily", "daily_stats", "pay_periods", "budgets",
        "budgets_summary", "goals", "trend", "insights",
    }
    assert rep["month"] == MONTH and rep["is_partial"] is False and rep["currency"] == "COP"
    assert rep["generated_at"].endswith("Z")

    # summary: 2 sueldos + freelance; sin transferencias
    s = rep["summary"]
    assert (s["income"], s["expense"], s["net"]) == ("2350000.00", "1454300.00", "895700.00")
    assert s["savings_rate"] == 38.1
    assert s["prev"] == {"income": "2000000.00", "expense": "1378300.00", "net": "621700.00", "savings_rate": 31.1}
    assert (s["income_change_pct"], s["expense_change_pct"], s["net_change_pct"]) == (17.5, 5.5, 44.1)


async def test_expense_and_income_by_category(api, data):
    rep = await get_report(api)
    exp = rep["expense_by_category"]
    assert [c["name"] for c in exp] == ["Hogar/Arriendo", "Comida", "Servicios", "Entretenimiento", "Salud"]
    by = {c["name"]: c for c in exp}
    assert by["Comida"]["total"] == "452300.00" and by["Comida"]["prev_total"] == "383300.00"
    assert by["Comida"]["change_pct"] == 18.0 and by["Comida"]["count"] == 3 and by["Comida"]["percent"] == 31.1
    assert by["Hogar/Arriendo"]["change_pct"] == 0.0 and by["Hogar/Arriendo"]["percent"] == 48.1
    assert by["Entretenimiento"]["prev_total"] == "0.00" and by["Entretenimiento"]["change_pct"] is None
    # una categoría que bajó a 0 sigue apareciendo, con -100 %
    assert by["Salud"]["total"] == "0.00" and by["Salud"]["prev_total"] == "100000.00"
    assert by["Salud"]["change_pct"] == -100.0 and by["Salud"]["count"] == 0 and by["Salud"]["percent"] == 0.0
    assert set(by["Comida"]) == {"category_id", "name", "color", "icon", "total", "prev_total", "change_pct", "percent", "count"}

    inc = {c["name"]: c for c in rep["income_by_category"]}
    assert list(inc) == ["Salario", "Freelance"]
    assert inc["Salario"]["total"] == "2000000.00" and inc["Salario"]["count"] == 2 and inc["Salario"]["is_new"] is False
    assert inc["Salario"]["change_pct"] == 0.0 and inc["Salario"]["percent"] == 85.1
    assert inc["Freelance"]["is_new"] is True and inc["Freelance"]["change_pct"] is None
    assert inc["Freelance"]["prev_total"] == "0.00" and inc["Freelance"]["percent"] == 14.9


async def test_top_expenses_daily_and_stats(api, data):
    rep = await get_report(api)
    top = rep["top_expenses"]
    assert [t["amount"] for t in top] == ["700000.00", "200000.00", "182000.00", "150000.00", "120000.00"]
    assert top[0] == {
        "transaction_id": top[0]["transaction_id"], "date": day(CUR, 5), "note": "Arriendo",
        "category": "Hogar/Arriendo", "account": "Bancolombia", "amount": "700000.00",
    }

    daily = rep["daily"]
    assert len(daily) == DIM and daily[0]["date"] == day(CUR, 1) and daily[-1]["date"] == CUR_END.isoformat()
    by_date = {d["date"]: d for d in daily}
    assert by_date[day(CUR, 5)]["expense"] == "700000.00"
    assert by_date[day(CUR, 6)]["expense"] == "0.00" and by_date[day(CUR, 6)]["income"] == "0.00"  # transferencia ignorada
    assert by_date[day(CUR, 9)]["income"] == "350000.00" and by_date[day(CUR, 9)]["is_payday"] is False  # freelance no es sueldo
    paydays = [d["date"] for d in daily if d["is_payday"]]
    assert paydays == [day(CUR, 15), CUR_END.isoformat()]

    st = rep["daily_stats"]
    assert st["max_day"] == day(CUR, 5) and st["max_day_expense"] == "700000.00"
    assert st["no_spend_days"] == DIM - 6  # días con gasto: 5, 8, 12, 18, 20 y 24
    assert st["avg_daily_expense"] == f"{1454300 / DIM:.2f}"


async def test_pay_periods_crossing_the_month(api, data):
    rep = await get_report(api)
    periods = rep["pay_periods"]
    starts = [p["start"] for p in periods]
    assert starts == sorted(starts) and len(periods) == 3
    # sueldos el 15 y el último día: [fin mes anterior, 14] · [15, penúltimo] · [último, 14 del mes siguiente]
    assert periods[0]["start"] == last_of_month(PREV).isoformat() and periods[0]["end"] == day(CUR, 14)
    assert periods[1]["start"] == day(CUR, 15) and periods[1]["end"] == (CUR_END - timedelta(days=1)).isoformat()
    assert periods[2]["start"] == CUR_END.isoformat()
    assert periods[2]["end"] == (CUR_END + timedelta(days=14)).isoformat()  # cruza al mes siguiente
    assert all(p["source"] == "paycheck" for p in periods)
    # el contenido de cada periodo usa las mismas métricas que /reports/pay-periods
    assert periods[0]["income"] == "1350000.00"  # sueldo del último día del mes anterior + freelance del día 9
    assert periods[1]["income"] == "1000000.00" and periods[1]["expense"] == "404300.00"
    assert {"days", "days_elapsed", "days_remaining", "in_progress", "spent_per_day", "available_per_day",
            "spent_percent", "time_percent", "status", "by_category"} <= set(periods[0])
    assert periods[0]["status"] in ("ahorro", "justo", "deficit")


async def test_budgets_summary_goals_and_trend(api, data):
    rep = await get_report(api)
    budgets = {b["category_id"]: b for b in rep["budgets"]}
    cats = data["cats"]
    assert budgets[cats["Entretenimiento"]["id"]]["status"] == "exceeded"
    assert budgets[cats["Comida"]["id"]]["status"] == "ok" and budgets[cats["Comida"]["id"]]["spent"] == "452300.00"
    assert budgets[cats["Hogar/Arriendo"]["id"]]["status"] == "warning"
    assert rep["budgets_summary"] == {"ok": 1, "warning": 1, "exceeded": 1}
    assert set(rep["budgets"][0]) == {"id", "category_id", "month", "amount_limit", "alert_threshold", "spent", "remaining", "percent", "status"}
    assert rep["budgets"][0]["month"] == MONTH

    (g,) = rep["goals"]
    # el aporte de hoy (posterior al mes) no cuenta: ahorro a fin de mes = 200.000 + 300.000
    assert g["saved"] == "500000.00" and g["percent"] == 16.7 and g["contributed_this_month"] == "300000.00"
    assert g["monthly_needed"] == "208333.33" and g["status"] == "on_track"
    assert set(g) == {"id", "name", "color", "target_amount", "saved", "percent", "contributed_this_month", "monthly_needed", "status"}

    trend = rep["trend"]
    assert len(trend) == 6 and trend[-1]["month"] == MONTH and trend[-2]["month"] == PREV.strftime("%Y-%m")
    assert trend[-1] == {"month": MONTH, "income": "2350000.00", "expense": "1454300.00", "net": "895700.00", "savings_rate": 38.1}
    assert trend[-2]["expense"] == "1378300.00"
    assert trend[0]["income"] == "0.00" and trend[0]["savings_rate"] == 0.0  # meses sin datos


async def test_insights_are_computed_by_rules(api, data):
    rep = await get_report(api)
    ins = rep["insights"]
    assert 2 <= len(ins) <= 6
    assert all(set(i) == {"kind", "tone", "text"} for i in ins)
    kinds = [i["kind"] for i in ins]
    assert kinds[0] == "budget_exceeded"  # la más relevante
    texts = {i["kind"]: i["text"] for i in ins}
    assert texts["budget_exceeded"] == "Entretenimiento superó su presupuesto por $ 20.000."
    assert texts["category_up"] == f"Gastaste 18 % más en Comida que en {PREV_MONTH_NAME} ($ 69.000 más)."
    assert texts["new_income"] == "Recibiste un ingreso nuevo por Freelance: $ 350.000."
    assert texts["savings_rate"].startswith("Tu tasa de ahorro fue 38,1 %: superas la meta sugerida del 20 %")
    assert texts["category_down"] == f"No gastaste nada en Salud este mes (en {PREV_MONTH_NAME} fueron $ 100.000)."
    assert {i["tone"] for i in ins} <= {"positive", "warning", "neutral"}


async def test_current_month_is_partial_and_daily_stops_today(api, data):
    cur = first_of_month(TODAY).strftime("%Y-%m")
    rep = await get_report(api, cur)
    assert rep["is_partial"] is True and rep["month"] == cur
    assert len(rep["daily"]) == TODAY.day and rep["daily"][-1]["date"] == TODAY.isoformat()
    assert rep["summary"]["prev"]["income"] == "2350000.00"  # el mes anterior es el del reporte de los datos
    assert 2 <= len(rep["insights"]) <= 6


async def test_user_without_data_gets_a_valid_report(api):
    rep = await get_report(api)
    s = rep["summary"]
    assert (s["income"], s["expense"], s["net"], s["savings_rate"]) == ("0.00", "0.00", "0.00", 0.0)
    assert s["income_change_pct"] is None and s["expense_change_pct"] is None and s["net_change_pct"] is None
    assert rep["expense_by_category"] == [] and rep["income_by_category"] == [] and rep["top_expenses"] == []
    assert rep["goals"] == [] and rep["budgets"] == [] and rep["budgets_summary"] == {"ok": 0, "warning": 0, "exceeded": 0}
    assert len(rep["trend"]) == 6 and len(rep["daily"]) == DIM
    assert rep["daily_stats"]["max_day"] is None and rep["daily_stats"]["no_spend_days"] == DIM
    assert 2 <= len(rep["insights"]) <= 6
    assert len(rep["pay_periods"]) >= 1  # respaldo de calendario (1-15 y 16-fin)
    assert all(p["source"] == "calendar" for p in rep["pay_periods"])


# ---------------- validaciones y seguridad ----------------
async def test_future_month_is_400_and_bad_format_is_422(api):
    nxt = add_months(first_of_month(TODAY), 1).strftime("%Y-%m")
    far = add_months(first_of_month(TODAY), 14).strftime("%Y-%m")
    for m in (nxt, far):
        r = await api.get(f"{R}/{m}")
        assert r.status_code == 400 and "futuro" in r.json()["detail"]
        assert (await api.get(f"{R}/{m}.pdf")).status_code == 400
    for bad in ("2026-13", "2026-00", "abc", "2026-1", "26-10", "0000-01", "2026-10-01"):
        assert (await api.get(f"{R}/{bad}")).status_code == 422, bad
        assert (await api.get(f"{R}/{bad}.pdf")).status_code == 422, bad


async def test_requires_auth_and_isolates_users(client, api, data):
    anon = await client.get(f"{R}/{MONTH}", headers={"Authorization": ""})
    assert anon.status_code == 401
    other = await make_user("otra@example.com")
    token = await login(client, other.email)
    r = await client.get(f"{R}/{MONTH}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    rep = r.json()
    assert rep["summary"]["income"] == "0.00" and rep["expense_by_category"] == [] and rep["goals"] == []


# ---------------- PDF ----------------
@pytest_asyncio.fixture
async def stub_renderer():
    from app.api.deps import get_report_renderer
    from app.main import app

    class Stub:
        def __init__(self):
            self.received = []

        async def render(self, report):
            self.received.append(report)
            return b"%PDF-1.7\n%stub"

    stub = Stub()
    app.dependency_overrides[get_report_renderer] = lambda: stub
    yield stub
    app.dependency_overrides.pop(get_report_renderer, None)


async def test_pdf_endpoint_wiring_with_stub_renderer(api, data, stub_renderer):
    r = await api.get(f"{R}/{MONTH}.pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.headers["content-disposition"] == f'attachment; filename="bolsillo_reporte_{MONTH}.pdf"'
    assert r.content.startswith(b"%PDF")
    (rep,) = stub_renderer.received
    assert rep.month == CUR and str(rep.summary.income) == "2350000.00" and len(rep.insights) >= 2
    assert rep.outlook  # "Para el próximo mes" listo para el PDF
    # la ruta JSON no captura ".pdf": ambas siguen siendo distintas
    assert (await api.get(f"{R}/{MONTH}")).headers["content-type"] == "application/json"


@requires_weasyprint
async def test_real_pdf_has_three_pages(api, data):
    r = await api.get(f"{R}/{MONTH}.pdf")
    assert r.status_code == 200, r.text[:300]
    assert r.headers["content-type"] == "application/pdf"
    assert r.headers["content-disposition"] == f'attachment; filename="bolsillo_reporte_{MONTH}.pdf"'
    assert r.content.startswith(b"%PDF")
    from pypdf import PdfReader

    pdf = PdfReader(io.BytesIO(r.content))
    assert len(pdf.pages) == 3
    text = pdf.pages[0].extract_text()
    assert "reporte mensual" in text.lower() and "Lo más importante" in text  # el kicker va en mayúsculas
    assert f"Reporte de {month_name(CUR)} {CUR.year}" in text
    assert "Entretenimiento superó su presupuesto" in text.replace("\n", " ")


@requires_weasyprint
async def test_real_pdf_for_empty_account_and_current_month(api):
    for m in (MONTH, first_of_month(TODAY).strftime("%Y-%m")):
        r = await api.get(f"{R}/{m}.pdf")
        assert r.status_code == 200 and r.content.startswith(b"%PDF")
        from pypdf import PdfReader

        assert len(PdfReader(io.BytesIO(r.content)).pages) == 3
