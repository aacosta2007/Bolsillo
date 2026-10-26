"""Adaptadores de generación de reportes (PDF)."""
from __future__ import annotations

from functools import lru_cache

from app.application.ports import ReportRenderer


@lru_cache
def build_report_renderer() -> ReportRenderer:
    """WeasyPrint + Jinja2. Se importa aquí para que la API arranque aunque falten las librerías de sistema."""
    from app.infrastructure.reporting.weasy_renderer import WeasyReportRenderer

    return WeasyReportRenderer()
