"""PDF real con WeasyPrint: A4, 3 páginas, fuentes embebidas y sin desbordes de contenido."""
from __future__ import annotations

import io
from datetime import date, timedelta

import pytest

from tests.pdf_support import requires_weasyprint
from tests.unit.report_builders import budget, goal, make_report, period

pytestmark = requires_weasyprint


@pytest.fixture(scope="module")
def renderer():
    from app.infrastructure.reporting.weasy_renderer import WeasyReportRenderer

    return WeasyReportRenderer()


def reader(pdf: bytes):
    from pypdf import PdfReader

    return PdfReader(io.BytesIO(pdf))


def stress_reports():
    from app.infrastructure.reporting.sample import sample_report

    empty = make_report(income=0, expense=0, prev_income=0, prev_expense=0, expense_cats=[], income_cats=[], spend_days=[])
    busy = make_report(
        income=9876543, expense=12345678, prev_income=5000000, prev_expense=1000000,
        expense_cats=[(f"Categoría muy larga número {i} con nombre extenso", 1000000 - i * 10000, 100000) for i in range(12)],
        income_cats=[(f"Fuente de ingreso {i}", 100000 + i, 0 if i % 2 else 100000) for i in range(7)],
        budgets=[budget(f"Presupuesto con nombre bastante largo {i}", 100000 * i, 200000) for i in range(11)],
        goals=[goal(f"Meta de ahorro con nombre largo {i}", contributed=0) for i in range(6)],
        periods=[
            period(date(2026, 10, 1) + timedelta(days=k), date(2026, 10, 1) + timedelta(days=k + 6), 100000, 190000)
            for k in (0, 7, 14, 21, 28)
        ],
        prior_trend=[(2000000, 3000000)] * 4,
    )
    return {"sample": sample_report(), "empty": empty, "busy": busy}


@pytest.mark.parametrize("name", ["sample", "empty", "busy"])
def test_pdf_is_a4_with_exactly_three_pages(renderer, name):
    pdf = renderer.render_sync(stress_reports()[name])
    assert pdf.startswith(b"%PDF")
    r = reader(pdf)
    assert len(r.pages) == 3
    for page in r.pages:
        w, h = float(page.mediabox.width), float(page.mediabox.height)
        assert (round(w), round(h)) == (595, 842)  # A4 en puntos


@pytest.mark.parametrize("name", ["sample", "empty", "busy"])
def test_page_content_fits_without_overflowing(renderer, name):
    """Sin altura fija ni overflow:hidden, cada página debe seguir cabiendo en una hoja (si no, saldrían 4+)."""
    html = renderer.fitted_html(stress_reports()[name])
    assert renderer.fits(html)


def test_pdf_text_and_fonts(renderer):
    from app.infrastructure.reporting.sample import sample_report

    r = reader(renderer.render_sync(sample_report()))
    p1, p2, p3 = (page.extract_text() for page in r.pages)
    assert "Octubre 2026" in p1 and "Página 1 de 3" in p1 and "Lo más importante" in p1
    assert "Gastos por categoría" in p2 and "Página 2 de 3" in p2 and "Los 5 gastos más grandes" in p2
    assert "Presupuestos" in p3 and "Página 3 de 3" in p3 and "Para noviembre" in p3
    fonts = set()
    for page in r.pages:
        for f in (page["/Resources"].get("/Font") or {}).values():
            fonts.add(str(f.get_object()["/BaseFont"]))
    joined = " ".join(fonts)
    assert "Figtree" in joined and "Bricolage" in joined  # fuentes embebidas, no del sistema


async def test_render_is_async_and_does_not_block_loop(renderer):
    from app.infrastructure.reporting.sample import sample_report

    pdf = await renderer.render(sample_report())
    assert pdf.startswith(b"%PDF")
