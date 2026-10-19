/**
 * Dinero: la API entrega strings decimales ("1234500.00"). Nunca pasamos por float:
 * se formatea y se suma con BigInt sobre centavos.
 */

export interface ParsedMoney {
  negative: boolean;
  /** Parte entera sin signo, sin ceros a la izquierda ("0" si vacío). */
  int: string;
  /** Siempre 2 dígitos. */
  cents: string;
}

export function parseMoney(value: string | number | null | undefined): ParsedMoney {
  let s = value === null || value === undefined ? '0' : String(value).trim();
  if (!s) s = '0';
  const negative = s.startsWith('-') || s.startsWith('−');
  s = s.replace(/^[-−+]/, '');
  const [i = '0', f = ''] = s.split('.');
  const int = (i.replace(/\D/g, '').replace(/^0+(?=\d)/, '') || '0');
  const cents = (f.replace(/\D/g, '') + '00').slice(0, 2);
  const isZero = /^0+$/.test(int) && cents === '00';
  return { negative: negative && !isZero, int, cents };
}

function groupThousands(int: string): string {
  return int.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}

/** "$ 1.234.500" (sin decimales si son ,00; con coma si no: "$ 1.234,50"). */
export function formatMoney(value: string | number | null | undefined, opts: { symbol?: boolean } = {}): string {
  const { negative, int, cents } = parseMoney(value);
  const num = groupThousands(int) + (cents === '00' ? '' : `,${cents}`);
  const body = opts.symbol === false ? num : `$ ${num}`;
  return negative ? `− ${body}` : body;
}

export type TxKind = 'income' | 'expense' | 'transfer';

/** Gasto "− $ 24.500", ingreso "+ $ 3.500.000", transferencia "$ 300.000". */
export function formatSigned(type: TxKind, value: string | number): string {
  const body = formatMoney(value);
  if (type === 'expense') return `− ${body}`;
  if (type === 'income') return `+ ${body}`;
  return body;
}

export function toCents(value: string | number | null | undefined): bigint {
  const { negative, int, cents } = parseMoney(value);
  const n = BigInt(int) * 100n + BigInt(cents);
  return negative ? -n : n;
}

export function fromCents(c: bigint): string {
  const neg = c < 0n;
  const abs = neg ? -c : c;
  const int = abs / 100n;
  const frac = (abs % 100n).toString().padStart(2, '0');
  return `${neg ? '-' : ''}${int}.${frac}`;
}

export function sumMoney(values: Array<string | number>): string {
  return fromCents(values.reduce<bigint>((acc, v) => acc + toCents(v), 0n));
}

/** Porcentaje entero (0–∞) de a sobre b, calculado con BigInt. */
export function percentOf(a: string, b: string): number {
  const d = toCents(b);
  if (d <= 0n) return 0;
  return Number((toCents(a) * 1000n) / d) / 10;
}

/** Dígitos tecleados en el keypad ("24500") → monto API ("24500.00"). */
export function digitsToAmount(digits: string): string {
  const clean = digits.replace(/\D/g, '').replace(/^0+/, '');
  return `${clean || '0'}.00`;
}

/** Monto API → dígitos del keypad (solo parte entera). */
export function amountToDigits(value: string): string {
  const { int } = parseMoney(value);
  return int === '0' ? '' : int;
}

/** Interpreta lo que escribe una persona ("1.200.000", "1200000,50") → "1200000.50" o null. */
export function parseUserAmount(input: string): string | null {
  const s = input.trim().replace(/\s|\$/g, '');
  if (!s) return null;
  let normalized = s;
  if (s.includes(',')) normalized = s.replace(/\./g, '').replace(',', '.');
  else if (/^\d{1,3}(\.\d{3})+$/.test(s)) normalized = s.replace(/\./g, '');
  if (!/^\d+(\.\d{1,2})?$/.test(normalized)) return null;
  const { int, cents } = parseMoney(normalized);
  return `${int}.${cents}`;
}

/** 39,9 % (coma decimal, espacio antes de %). */
export function formatPercent(n: number, digits = 1): string {
  const s = n.toFixed(digits).replace(/\.0+$/, "").replace(".", ",");
  return `${s} %`;
}
