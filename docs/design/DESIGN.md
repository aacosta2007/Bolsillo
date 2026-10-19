# Bolsillo — Guía de diseño

Fuente: canvas de Claude Design https://claude.ai/artifact/7UTsH9S86jJ6DXC2ZfTjUP
Los archivos `*.dc.html` de esta carpeta son las pantallas de referencia (390×844). Úsalos como especificación visual:
estructura, espaciados, radios, colores y textos. La sintaxis `{{...}}`, `<sc-for>`, `<sc-if>` es del editor de diseño, no la copies; tradúcela a componentes React.

## Tokens
| Token | Valor | Uso |
|---|---|---|
| `bg` | `#F4F6F3` | Fondo de app |
| `surface` | `#FFFFFF` | Tarjetas, nav inferior |
| `ink` | `#16201B` | Texto principal, tarjeta oscura de presupuestos |
| `muted` | `#55615B` | Texto secundario |
| `line` | `#DDE3DE` / `#EEF1EE` | Bordes / separadores |
| `primary` | `#0F5E55` (hover `#0B4740`, tint `#E3F0ED`) | Marca, CTA, activo |
| `income` | `#1D4ED8` (tint `#E4ECFD`) | Ingresos |
| `expense` | `#B33A0A` (tint `#FDECE2`) | Gastos |
| `warning` | barra `#E58A2E`, chip `#FFF0DC`/`#8A4A0F` | Presupuesto ≥ umbral |
| `danger` | barra `#B33A0A`, chip `#FDE3D6`/`#8A2C07` | Presupuesto excedido |
| Paleta de categorías | `#0F5E55 #C2410C #2563EB #F2A65A #93C5BB #6D28D9 #BE185D #0E7490 #B7791F` | Gráficas y avatares |

Tipografía: **Bricolage Grotesque** 700 (títulos y montos grandes) + **Figtree** 400–700 (texto). Números con `font-variant-numeric: tabular-nums`.
Radios: tarjetas 20–24px, controles 12–14px, chips 999px. Toques ≥ 44px. Padding de pantalla 20px.
Montos formateados `es-CO`: `$ 1.234.500`; gasto con prefijo `− `, ingreso `+ `.

## Pantallas
1. **Main** (Inicio/Dashboard): saludo + mes, tarjeta de saldo total (primary) con ingresos/gastos/ahorro, alerta de presupuesto en riesgo, dona por categoría, barras ingresos vs gastos 6 meses, últimos movimientos.
2. **Movimientos**: buscador, chips de filtro (Todos/Gastos/Ingresos/Transferencias/Mes), resumen del mes, lista agrupada por día.
3. **Agregar** (pantalla completa desde el botón central): selector Gasto/Ingreso/Transferir, monto grande, grilla de categorías, cuenta, fecha, nota, teclado numérico, botón Guardar. En transferencia: cuenta origen/destino en vez de categorías.
4. **Presupuestos**: selector de mes, tarjeta oscura de total gastado vs presupuestado y gasto diario sugerido, tarjetas por categoría con barra y chip de %, copiar del mes anterior.
5. **Metas**: pestañas Ahorro / Recurrentes. Metas con anillo de progreso, aporte rápido (+). Recurrentes con total fijo mensual y próximo cobro.

Navegación inferior fija: Inicio · Movimientos · (+) · Presupuestos · Metas. Ajustes, cuentas y categorías se acceden desde el ícono de perfil/engranaje en el encabezado de Inicio.
