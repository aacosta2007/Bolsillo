"""Gráficas del reporte como SVG inline generado en Python (sin matplotlib).

Cada helper devuelve una cadena SVG bien formada. Los colores y medidas salen del diseño
`docs/design/v2/PDF1-3.dc.html`. Las funciones no dependen de WeasyPrint, así que se pueden
probar sin las librerías de sistema.
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from xml.sax.saxutils import escape, quoteattr

INK = "#16201B"
MUTED = "#55615B"
FAINT = "#7A857F"
LINE = "#E2E7E3"
LINE_SOFT = "#EEF1EE"
GRID = "#DDE3DE"
PRIMARY = "#0F5E55"
INCOME = "#1D4ED8"
INCOME_BAR = "#2563EB"
EXPENSE_BAR = "#C2410C"
DANGER = "#B33A0A"
WARNING = "#E58A2E"
FONT = "Figtree, sans-serif"
SVG_NS = 'xmlns="http://www.w3.org/2000/svg"'


def _n(v: float) -> str:
    """Número compacto para atributos SVG."""
    text = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def _svg(width: float, height: float, body: str, *, aria: str = "", viewbox: str | None = None) -> str:
    vb = viewbox or f"0 0 {_n(width)} {_n(height)}"
    label = f' role="img" aria-label={quoteattr(aria)}' if aria else ""
    return f'<svg {SVG_NS} width="{_n(width)}" height="{_n(height)}" viewBox="{vb}"{label}>{body}</svg>'


def _top_rounded_bar(x: float, y: float, w: float, h: float, r: float, fill: str) -> str:
    if h <= 0 or w <= 0:
        return ""
    r = max(0.0, min(r, h, w / 2))
    d = (
        f"M{_n(x)},{_n(y + h)} L{_n(x)},{_n(y + r)} Q{_n(x)},{_n(y)} {_n(x + r)},{_n(y)} "
        f"L{_n(x + w - r)},{_n(y)} Q{_n(x + w)},{_n(y)} {_n(x + w)},{_n(y + r)} L{_n(x + w)},{_n(y + h)} Z"
    )
    return f'<path d="{d}" fill="{fill}"/>'


# ---------- Dona por categoría ----------
def donut(segments: Sequence[tuple[float, str]], *, size: int = 180, aria: str = "Distribución de gastos") -> str:
    """Dona (r=38, trazo 18 sobre viewBox 100) como el diseño. `segments` = [(valor, color)]."""
    r = 38.0
    circ = 2 * math.pi * r
    total = sum(max(v, 0.0) for v, _ in segments)
    body = f'<circle cx="50" cy="50" r="{_n(r)}" fill="none" stroke="{LINE_SOFT}" stroke-width="18"/>'
    if total > 0:
        offset = 0.0
        arcs = []
        for value, color in segments:
            if value <= 0:
                continue
            length = value / total * circ
            arcs.append(
                f'<circle cx="50" cy="50" r="{_n(r)}" fill="none" stroke="{color}" stroke-width="18" '
                f'stroke-dasharray="{_n(length)} {_n(circ - length)}" stroke-dashoffset="{_n(-offset)}"/>'
            )
            offset += length
        body += f'<g transform="rotate(-90 50 50)">{"".join(arcs)}</g>'
    return _svg(size, size, body, aria=aria, viewbox="0 0 100 100")


# ---------- Barra apilada horizontal ----------
def stacked_bar(
    segments: Sequence[tuple[float, str]], *, width: float = 300, height: float = 26, radius: float = 8
) -> str:
    total = sum(max(v, 0.0) for v, _ in segments)
    clip_id = "sb-clip"
    body = (
        f'<defs><clipPath id="{clip_id}"><rect width="{_n(width)}" height="{_n(height)}" rx="{_n(radius)}"/></clipPath></defs>'
        f'<rect width="{_n(width)}" height="{_n(height)}" rx="{_n(radius)}" fill="{LINE_SOFT}"/>'
    )
    if total > 0:
        x = 0.0
        parts = []
        for value, color in segments:
            if value <= 0:
                continue
            w = value / total * width
            parts.append(f'<rect x="{_n(x)}" y="0" width="{_n(w + 0.5)}" height="{_n(height)}" fill="{color}"/>')
            x += w
        body += f'<g clip-path="url(#{clip_id})">{"".join(parts)}</g>'
    return _svg(width, height, body, aria="Reparto de gastos por categoría")


# ---------- Barras agrupadas ingresos / gastos ----------
def grouped_bars(
    labels: Sequence[str],
    incomes: Sequence[float],
    expenses: Sequence[float],
    *,
    highlight: int | None = None,
    width: float = 682,
    height: float = 170,
) -> str:
    """Barras de ingresos (azul) y gastos (naranja) por mes, con etiquetas; el mes `highlight` en negrita."""
    n = len(labels)
    label_h, plot_h = 22.0, height - 22.0
    bar_w, gap_in = 22.0, 4.0
    top = 8.0
    scale_h = plot_h - top
    peak = max([*incomes, *expenses, 0.0])
    col_w = (width - 16) / max(n, 1)  # 8 px de margen a cada lado, como el diseño
    parts = [f'<line x1="0" y1="{_n(plot_h)}" x2="{_n(width)}" y2="{_n(plot_h)}" stroke="{LINE}" stroke-width="1"/>']
    for i, label in enumerate(labels):
        cx = 8 + col_w * i + col_w / 2
        for j, (value, color) in enumerate(((incomes[i], INCOME_BAR), (expenses[i], EXPENSE_BAR))):
            h = max(2.0, value / peak * scale_h) if peak > 0 and value > 0 else 0.0
            x = cx - bar_w - gap_in / 2 if j == 0 else cx + gap_in / 2
            parts.append(_top_rounded_bar(x, plot_h - h, bar_w, h, 4, color))
        strong = highlight == i
        parts.append(
            f'<text x="{_n(cx)}" y="{_n(plot_h + 16)}" text-anchor="middle" font-family="{FONT}" font-size="12" '
            f'font-weight="{700 if strong else 500}" fill="{INK if strong else MUTED}">{escape(label)}</text>'
        )
    return _svg(width, height, "".join(parts), aria="Ingresos y gastos de los últimos meses")


# ---------- Barras diarias del mes ----------
def daily_bars(
    values: Sequence[float],
    is_payday: Sequence[bool],
    day_numbers: Sequence[int],
    *,
    width: float = 682,
    height: float = 160,
    plot_height: float = 140,
    gap: float = 3,
    columns: int | None = None,
) -> str:
    """Una barra por día. Los días de pago se pintan de azul; los de gasto alto (> 2,75 × el promedio),
    de naranja; el resto, de verde. La escala se recorta para que un gasto atípico no aplaste el resto."""
    n = len(values)
    if n == 0:
        return _svg(width, height, "", aria="Gasto diario")
    avg = sum(values) / n
    high = avg * 2.75
    peak = max(values)
    cap = peak if peak <= high * 4 / 3 or high <= 0 else high * 4 / 3
    cols = max(columns or n, n)  # días del mes: en un mes parcial quedan columnas vacías a la derecha
    bar_w = (width - gap * (cols - 1)) / cols
    usable = plot_height - 4
    parts = [f'<line x1="0" y1="{_n(plot_height)}" x2="{_n(width)}" y2="{_n(plot_height)}" stroke="{LINE}" stroke-width="1"/>']
    for i, (value, payday, day) in enumerate(zip(values, is_payday, day_numbers)):
        x = i * (bar_w + gap)
        h = max(2.0, min(value, cap) / cap * usable) if cap > 0 else 2.0
        if payday:
            color, h = INCOME, max(h, 8.0)
        elif high > 0 and value > high:
            color = EXPENSE_BAR
        else:
            color = PRIMARY
        parts.append(_top_rounded_bar(x, plot_height - h, bar_w, h, 3, color))
        if day == 1 or day % 5 == 0:
            parts.append(
                f'<text x="{_n(x + bar_w / 2)}" y="{_n(plot_height + 13)}" text-anchor="middle" font-family="{FONT}" '
                f'font-size="9" fill="{FAINT}">{day}</text>'
            )
    return _svg(width, height, "".join(parts), aria="Gasto diario del mes")


# ---------- Línea de tasa de ahorro ----------
def savings_line(
    values: Sequence[float], *, target: float = 20.0, width: float = 297, height: float = 150
) -> str:
    """Línea de la tasa de ahorro (%) por mes con la meta sugerida punteada. Los puntos quedan centrados
    en columnas iguales (la fila de etiquetas HTML usa la misma cuadrícula)."""
    n = len(values)
    lo = min(0.0, *values) if values else 0.0
    hi = max(target + 5, *values) if values else target + 5
    pad_top, pad_bottom = 14.0, 14.0
    plot = height - pad_top - pad_bottom

    def y_of(v: float) -> float:
        return pad_top + (hi - v) / (hi - lo) * plot

    col = width / max(n, 1)
    pts = [(col * i + col / 2, y_of(v)) for i, v in enumerate(values)]
    parts = [
        f'<line x1="0" y1="{_n(y_of(0))}" x2="{_n(width)}" y2="{_n(y_of(0))}" stroke="{GRID}" stroke-width="1"/>',
        f'<line x1="0" y1="{_n(y_of(target))}" x2="{_n(width)}" y2="{_n(y_of(target))}" stroke="{GRID}" '
        'stroke-width="1" stroke-dasharray="4 4"/>',
    ]
    if len(pts) > 1:
        poly = " ".join(f"{_n(x)},{_n(y)}" for x, y in pts)
        parts.append(
            f'<polyline points="{poly}" fill="none" stroke="{PRIMARY}" stroke-width="3" '
            'stroke-linejoin="round" stroke-linecap="round"/>'
        )
    for x, y in pts:
        parts.append(f'<circle cx="{_n(x)}" cy="{_n(y)}" r="4.5" fill="#FFFFFF" stroke="{PRIMARY}" stroke-width="2.5"/>')
    return _svg(width, height, "".join(parts), aria="Tasa de ahorro mensual")


# ---------- Anillo de progreso de una meta ----------
def goal_ring(percent: float, color: str, *, size: int = 56, aria: str = "") -> str:
    r = 15.0
    circ = 2 * math.pi * r
    fraction = max(0.0, min(percent, 100.0)) / 100
    label = f"{int(round(percent))}%"
    body = f'<circle cx="18" cy="18" r="{_n(r)}" fill="none" stroke="{LINE_SOFT}" stroke-width="4"/>'
    if fraction > 0:
        body += (
            f'<circle cx="18" cy="18" r="{_n(r)}" fill="none" stroke="{color}" stroke-width="4" '
            f'stroke-linecap="round" stroke-dasharray="{_n(circ * fraction)} {_n(circ)}" transform="rotate(-90 18 18)"/>'
        )
    body += (
        f'<text x="18" y="21" text-anchor="middle" font-size="8.5" font-weight="700" fill="{INK}" '
        f'font-family="{FONT}">{label}</text>'
    )
    return _svg(size, size, body, aria=aria or f"Progreso {label}", viewbox="0 0 36 36")


# ---------- Barra de presupuesto con marca de umbral ----------
def budget_bar(
    percent: float, threshold_percent: float, color: str, *, width: float = 310, height: float = 18
) -> str:
    bar_h = 12.0
    y = (height - bar_h) / 2
    fill_w = max(0.0, min(percent, 100.0)) / 100 * width
    mark_x = max(1.0, min(threshold_percent, 100.0) / 100 * width)
    body = f'<rect x="0" y="{_n(y)}" width="{_n(width)}" height="{_n(bar_h)}" rx="6" fill="{LINE_SOFT}"/>'
    if fill_w > 0:
        body += f'<rect x="0" y="{_n(y)}" width="{_n(max(fill_w, bar_h))}" height="{_n(bar_h)}" rx="6" fill="{color}"/>'
    body += f'<rect x="{_n(mark_x - 1)}" y="0" width="2" height="{_n(height)}" fill="#A9B5AE"/>'
    return _svg(width, height, body, aria=f"Presupuesto usado: {int(round(percent))} %")


# ---------- Íconos (no dependen de que la fuente tenga ▲ ▼ ★; el color se pone en el <svg>) ----------
_ICON_PATHS = {
    "up": '<path d="M5 1 L9.5 9 L0.5 9 Z" />',
    "down": '<path d="M5 9 L9.5 1 L0.5 1 Z" />',
    "star": '<path d="M5 0.6 L6.3 3.5 L9.5 3.9 L7.1 6 L7.8 9.2 L5 7.6 L2.2 9.2 L2.9 6 L0.5 3.9 L3.7 3.5 Z" />',
    "plus": '<path d="M4.1 1 H5.9 V4.1 H9 V5.9 H5.9 V9 H4.1 V5.9 H1 V4.1 H4.1 Z" />',
    "bang": '<path d="M4 0.8 H6 L5.7 6 H4.3 Z M4 7.2 H6 V9.2 H4 Z" />',
    "check": '<path d="M1 5.2 L2.4 3.8 L4.1 5.5 L7.6 1.7 L9 3.1 L4.1 8.2 Z" />',
    "dot": '<circle cx="5" cy="5" r="2.4" />',
}


def icon(name: str, *, size: int = 10, color: str = INK) -> str:
    """Ícono en un SVG de 10x10. El color va explícito (WeasyPrint no resuelve currentColor en SVG inline)."""
    path = _ICON_PATHS.get(name, _ICON_PATHS["dot"])
    return (
        f'<svg {SVG_NS} class="ico" width="{size}" height="{size}" viewBox="0 0 10 10" '
        f'fill="{color}" aria-hidden="true">{path}</svg>'
    )
