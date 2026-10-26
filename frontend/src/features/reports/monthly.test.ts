import { describe, expect, it } from 'vitest';
import { defaultReportMonth, describeChange, describePoints, resolveReportMonth, TONE_CLASS } from './monthly';

// 17:00 UTC = 12:00 en Bogotá (UTC-5): mismo día calendario.
const at = (iso: string) => new Date(`${iso}T17:00:00Z`);

describe('defaultReportMonth', () => {
  it('días 1–5 → mes anterior', () => {
    expect(defaultReportMonth('America/Bogota', at('2026-11-01'))).toBe('2026-10');
    expect(defaultReportMonth('America/Bogota', at('2026-11-05'))).toBe('2026-10');
    expect(defaultReportMonth('America/Bogota', at('2027-01-03'))).toBe('2026-12');
  });
  it('día 6 en adelante → mes en curso', () => {
    expect(defaultReportMonth('America/Bogota', at('2026-11-06'))).toBe('2026-11');
    expect(defaultReportMonth('America/Bogota', at('2026-10-25'))).toBe('2026-10');
  });
  it('usa la zona horaria del usuario (1 nov 02:00 UTC sigue siendo 31 oct en Bogotá)', () => {
    expect(defaultReportMonth('America/Bogota', new Date('2026-11-01T02:00:00Z'))).toBe('2026-10');
  });
});

describe('resolveReportMonth', () => {
  const now = at('2026-10-25');
  it('acepta un mes válido y no futuro', () => {
    expect(resolveReportMonth('2026-09', 'America/Bogota', now)).toBe('2026-09');
    expect(resolveReportMonth('2026-10', 'America/Bogota', now)).toBe('2026-10');
  });
  it('rechaza futuro o formato inválido y cae al mes por defecto', () => {
    expect(resolveReportMonth('2026-11', 'America/Bogota', now)).toBe('2026-10');
    expect(resolveReportMonth('2026-13', 'America/Bogota', now)).toBe('2026-10');
    expect(resolveReportMonth('basura', 'America/Bogota', now)).toBe('2026-10');
    expect(resolveReportMonth(null, 'America/Bogota', now)).toBe('2026-10');
  });
});

describe('describeChange', () => {
  it('gasto: subir es malo, bajar es bueno', () => {
    expect(describeChange(18, 'expense')).toEqual({ text: '▲ 18 %', sr: 'subió 18 %', tone: 'bad' });
    expect(describeChange(-20.5, 'expense')).toEqual({ text: '▼ 20,5 %', sr: 'bajó 20,5 %', tone: 'good' });
    expect(describeChange(-100, 'expense')?.tone).toBe('good');
  });
  it('ingreso/ahorro: subir es bueno, bajar es malo', () => {
    expect(describeChange(17.5, 'income')).toEqual({ text: '▲ 17,5 %', sr: 'subió 17,5 %', tone: 'good' });
    expect(describeChange(-5, 'income')?.tone).toBe('bad');
  });
  it('cero, nuevo y sin datos', () => {
    expect(describeChange(0, 'expense')).toEqual({ text: '= 0 %', sr: 'sin cambios', tone: 'neutral' });
    expect(describeChange(null, 'income', true)).toEqual({ text: 'nuevo', sr: 'nuevo este mes', tone: 'good' });
    expect(describeChange(null, 'expense')).toBeNull();
  });
  it('colores: bueno verde, malo naranja, neutro gris', () => {
    expect(TONE_CLASS.good).toBe('text-primary');
    expect(TONE_CLASS.bad).toBe('text-expense');
    expect(TONE_CLASS.neutral).toBe('text-muted');
  });
});

describe('describePoints', () => {
  it('puntos de tasa de ahorro', () => {
    expect(describePoints(28.3, 20.5)).toEqual({ text: '▲ 7,8 pts', sr: 'subió 7,8 puntos', tone: 'good' });
    expect(describePoints(10, 20)?.tone).toBe('bad');
    expect(describePoints(10, null)).toBeNull();
  });
});
