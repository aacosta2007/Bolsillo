"""Renderer del reporte mensual: Jinja2 genera el HTML y WeasyPrint lo convierte en PDF (A4, 3 páginas)."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from app.domain.monthly_report import MonthlyReport
from app.infrastructure.reporting.viewmodel import MAX_DENSITY, build_context, initial_density

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
PAGES = 3
FIT_CSS = ".page { height: auto !important; min-height: 296.5mm; overflow: visible !important; }"

for noisy in ("fontTools", "weasyprint"):  # el subconjunto de fuentes registra cientos de líneas INFO
    logging.getLogger(noisy).setLevel(logging.ERROR)


class WeasyReportRenderer:
    def __init__(self) -> None:
        self.env = Environment(
            loader=FileSystemLoader(TEMPLATES_DIR),
            autoescape=select_autoescape(["html"]),
            undefined=StrictUndefined,
        )

    def render_html(self, report: MonthlyReport, density: int | None = None) -> str:
        return self.env.get_template("report.html").render(**build_context(report, density))

    def fits(self, html: str) -> bool:
        """True si cada página cabe en una hoja: sin altura fija ni overflow:hidden, sobrarían hojas."""
        from weasyprint import CSS, HTML

        doc = HTML(string=html, base_url=str(BASE_DIR) + "/").render(stylesheets=[CSS(string=FIT_CSS)])
        return len(doc.pages) <= PAGES

    def fitted_html(self, report: MonthlyReport) -> str:
        """HTML con la densidad mínima que cabe en 3 hojas. Los textos reales varían (6 observaciones
        largas, 5 quincenas...): si la página 1 no cabe se compacta progresivamente en vez de recortarla."""
        density = initial_density(report)
        html = self.render_html(report, density)
        while density < MAX_DENSITY and not self.fits(html):
            density += 1
            html = self.render_html(report, density)
        return html

    def render_sync(self, report: MonthlyReport) -> bytes:
        # Import diferido: WeasyPrint carga pango/cairo al importarse y es bloqueante.
        from weasyprint import HTML

        return HTML(string=self.fitted_html(report), base_url=str(BASE_DIR) + "/").write_pdf()

    async def render(self, report: MonthlyReport) -> bytes:
        return await asyncio.to_thread(self.render_sync, report)
