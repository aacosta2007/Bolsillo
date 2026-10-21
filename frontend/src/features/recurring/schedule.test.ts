import { describe, expect, it } from 'vitest';
import {
  adjustWeekend,
  describeFrequency,
  formatDays,
  modeFromRule,
  monthOccurrences,
  monthlyEquivalentCents,
  parseDays,
  scheduleFromMode,
  upcomingOccurrences,
  type ScheduleInput,
} from './schedule';

const base: ScheduleInput = { frequency: 'monthly_days', interval: 1, days_of_month: '15,L', weekend_adjust: 'none', start_date: '2026-10-01' };

describe('monthOccurrences', () => {
  it('"15,L" en octubre 2026 (31 días)', () => expect(monthOccurrences([15, 'L'], 2026, 10)).toEqual(['2026-10-15', '2026-10-31']));
  it('"15,L" en noviembre 2026 (30 días)', () => expect(monthOccurrences([15, 'L'], 2026, 11)).toEqual(['2026-11-15', '2026-11-30']));
  it('"15,L" en febrero 2027 (28 días)', () => expect(monthOccurrences([15, 'L'], 2027, 2)).toEqual(['2027-02-15', '2027-02-28']));
  it('"15,L" en febrero 2028 (bisiesto)', () => expect(monthOccurrences([15, 'L'], 2028, 2)).toEqual(['2028-02-15', '2028-02-29']));
  it('"15,30" en febrero se ajusta al último día', () => expect(monthOccurrences([15, 30], 2027, 2)).toEqual(['2027-02-15', '2027-02-28']));
  it('"30,L" en febrero genera una sola fecha', () => expect(monthOccurrences([30, 'L'], 2027, 2)).toEqual(['2027-02-28']));
});

describe('parseDays / formatDays', () => {
  it('ordena números y deja L al final', () => expect(formatDays([20, 'L', 5])).toBe('5,20,L'));
  it('ignora inválidos y repetidos', () => expect(parseDays('15,x,15,40,L')).toEqual([15, 'L']));
});

describe('upcomingOccurrences', () => {
  it('quincena 15 y último desde el 1 oct 2026 cruza meses', () => {
    const r = upcomingOccurrences(base, 4);
    expect(r.map((o) => o.date)).toEqual(['2026-10-15', '2026-10-31', '2026-11-15', '2026-11-30']);
  });

  it('respeta start_date a mitad de mes', () => {
    const r = upcomingOccurrences({ ...base, start_date: '2026-10-16' }, 2);
    expect(r.map((o) => o.date)).toEqual(['2026-10-31', '2026-11-15']);
  });

  it('febrero 2027: 15 y 28', () => {
    const r = upcomingOccurrences({ ...base, start_date: '2027-02-01' }, 2);
    expect(r.map((o) => o.date)).toEqual(['2027-02-15', '2027-02-28']);
  });

  it('"30,L" en febrero: una sola fecha, luego marzo', () => {
    const r = upcomingOccurrences({ ...base, days_of_month: '30,L', start_date: '2027-02-01' }, 3);
    expect(r.map((o) => o.date)).toEqual(['2027-02-28', '2027-03-30', '2027-03-31']);
  });

  it('ajuste de fin de semana: sáb 31 oct a vie 30 oct; dom 15 nov a vie 13 nov', () => {
    const r = upcomingOccurrences({ ...base, weekend_adjust: 'previous_business_day' }, 4);
    expect(r).toEqual([
      { nominal: '2026-10-15', date: '2026-10-15', adjusted: false },
      { nominal: '2026-10-31', date: '2026-10-30', adjusted: true },
      { nominal: '2026-11-15', date: '2026-11-13', adjusted: true },
      { nominal: '2026-11-30', date: '2026-11-30', adjusted: false },
    ]);
  });

  it('respeta end_date', () => {
    expect(upcomingOccurrences({ ...base, end_date: '2026-10-20' }, 4)).toHaveLength(1);
  });

  it('mensual clásico día 31 se ajusta al último día del mes', () => {
    const r = upcomingOccurrences({ ...base, frequency: 'monthly', days_of_month: null, start_date: '2026-10-31' }, 3);
    expect(r.map((o) => o.date)).toEqual(['2026-10-31', '2026-11-30', '2026-12-31']);
  });

  it('semanal cada 1 semana', () => {
    const r = upcomingOccurrences({ ...base, frequency: 'weekly', days_of_month: null, start_date: '2026-10-15' }, 3);
    expect(r.map((o) => o.date)).toEqual(['2026-10-15', '2026-10-22', '2026-10-29']);
  });

  it('sin días elegidos no hay fechas', () => {
    expect(upcomingOccurrences({ ...base, days_of_month: '' })).toEqual([]);
  });

  it('adjustWeekend', () => {
    expect(adjustWeekend('2026-10-31')).toBe('2026-10-30');
    expect(adjustWeekend('2026-11-15')).toBe('2026-11-13');
    expect(adjustWeekend('2026-11-16')).toBe('2026-11-16');
  });
});

describe('monthlyEquivalentCents', () => {
  const c = 100_000_000n; // $ 1.000.000,00
  it('monthly_days: monto por cantidad de días', () => {
    expect(monthlyEquivalentCents(c, 'monthly_days', 1, 2)).toBe(200_000_000n);
    expect(monthlyEquivalentCents(c, 'monthly_days', 1, 3)).toBe(300_000_000n);
  });
  it('monthly: amount / interval', () => expect(monthlyEquivalentCents(c, 'monthly', 2)).toBe(50_000_000n));
  it('weekly: amount x 52 / 12 / interval, redondeado a centavos', () => {
    expect(monthlyEquivalentCents(100n, 'weekly', 1)).toBe(433n);
    expect(monthlyEquivalentCents(c, 'weekly', 1)).toBe(433_333_333n);
  });
  it('daily y yearly', () => {
    expect(monthlyEquivalentCents(1200n, 'daily', 1)).toBe(36_500n);
    expect(monthlyEquivalentCents(120_000n, 'yearly', 1)).toBe(10_000n);
  });
});

describe('modo y descripción', () => {
  it('modeFromRule', () => {
    expect(modeFromRule({ frequency: 'monthly_days', days_of_month: '15,L' })).toBe('q15L');
    expect(modeFromRule({ frequency: 'monthly_days', days_of_month: '15,30' })).toBe('q1530');
    expect(modeFromRule({ frequency: 'monthly_days', days_of_month: '5,20' })).toBe('custom');
    expect(modeFromRule({ frequency: 'monthly', days_of_month: null })).toBe('monthly');
    expect(modeFromRule({ frequency: 'yearly', days_of_month: null })).toBe('more');
  });
  it('scheduleFromMode ordena días personalizados', () => {
    expect(scheduleFromMode('custom', ['L', 20, 5], 'daily')).toEqual({ frequency: 'monthly_days', days_of_month: '5,20,L' });
    expect(scheduleFromMode('monthly', [], 'daily')).toEqual({ frequency: 'monthly', days_of_month: null });
  });
  it('describeFrequency', () => {
    const r = { interval: 1, start_date: '2026-01-05' };
    expect(describeFrequency({ ...r, frequency: 'monthly_days', days_of_month: '15,L' })).toBe('Quincenal · 15 y último día');
    expect(describeFrequency({ ...r, frequency: 'monthly_days', days_of_month: '5,20' })).toBe('Días 5, 20');
    expect(describeFrequency({ ...r, frequency: 'monthly', days_of_month: null })).toBe('Mensual · día 5');
  });
});
