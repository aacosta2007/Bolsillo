"""Soporte para pruebas que generan PDF: WeasyPrint necesita Pango; en Windows suele faltar (se corre en Docker)."""
import pytest

try:
    import weasyprint  # noqa: F401

    WEASYPRINT_OK = True
    WEASYPRINT_ERROR = ""
except Exception as exc:  # OSError (falta libpango) o ImportError
    WEASYPRINT_OK = False
    WEASYPRINT_ERROR = str(exc).strip().splitlines()[0] if str(exc).strip() else type(exc).__name__

requires_weasyprint = pytest.mark.skipif(
    not WEASYPRINT_OK,
    reason="WeasyPrint sin librerías de sistema (Pango/GTK); estas pruebas corren dentro del contenedor del API",
)
