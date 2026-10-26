import { describe, expect, it } from 'vitest';
import { payPeriodHighlights } from './summary';
import { makePeriod } from './fixtures';

const closed = (start: string, net: string, over = {}) =>
  makePeriod({ start, in_progress: false, net, status: Number(net) < 0 ? 'deficit' : 'ahorro', ...over });

describe('payPeriodHighlights', () => {
  it('elige la mejor quincena cerrada por neto e ignora la en curso', () => {
    const r = payPeriodHighlights([
      makePeriod({ net: '9999999.00' }),
      closed('2026-10-01', '97900.00'),
      closed('2026-09-15', '230000.00'),
      closed('2026-09-01', '150000.00'),
    ]);
    expect(r.best?.start).toBe('2026-09-15');
    expect(r.deficit).toBeNull();
    expect(r.longest).toBeNull();
  });

  it('detecta déficit y la quincena más larga', () => {
    const r = payPeriodHighlights([
      closed('2026-10-01', '100000.00'),
      closed('2026-09-15', '230000.00'),
      closed('2026-08-31', '50000.00', { days: 17 }),
      closed('2026-08-14', '-80000.00', { days: 15 }),
    ]);
    expect(r.best?.start).toBe('2026-09-15');
    expect(r.deficit?.start).toBe('2026-08-14');
    expect(r.longest?.start).toBe('2026-08-31');
  });

  it('sin quincenas cerradas no hay resumen; con todo negativo no hay "mejor"', () => {
    expect(payPeriodHighlights([makePeriod()])).toEqual({ best: null, deficit: null, longest: null });
    const r = payPeriodHighlights([closed('2026-09-15', '-5.00')]);
    expect(r.best).toBeNull();
    expect(r.deficit?.start).toBe('2026-09-15');
  });

  it('en empate gana la más reciente (primera de la lista)', () => {
    const r = payPeriodHighlights([closed('2026-10-01', '100.00'), closed('2026-09-15', '100.00')]);
    expect(r.best?.start).toBe('2026-10-01');
  });
});
