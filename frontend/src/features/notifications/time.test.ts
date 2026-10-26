import { describe, expect, it } from 'vitest';
import { relativeTime } from './time';

const now = new Date('2026-10-25T17:00:00Z'); // 12:00 en Bogotá
const tz = 'America/Bogota';

describe('relativeTime', () => {
  it('ahora y minutos', () => {
    expect(relativeTime('2026-10-25T16:59:40Z', tz, now)).toBe('ahora');
    expect(relativeTime('2026-10-25T16:35:00Z', tz, now)).toBe('hace 25 min');
  });
  it('horas el mismo día local', () => {
    expect(relativeTime('2026-10-25T15:00:00Z', tz, now)).toBe('hace 2 h');
  });
  it('ayer según la zona del usuario (no UTC)', () => {
    // 02:00 UTC del 25 = 21:00 del 24 en Bogotá
    expect(relativeTime('2026-10-25T02:00:00Z', tz, now)).toBe('ayer');
    expect(relativeTime('2026-10-24T20:00:00Z', tz, now)).toBe('ayer');
  });
  it('fecha corta y con año si es otro año', () => {
    expect(relativeTime('2026-10-15T14:00:00Z', tz, now)).toBe('15 oct');
    expect(relativeTime('2025-12-01T14:00:00Z', tz, now)).toBe('1 dic 2025');
  });
  it('fecha inválida o futura no rompe', () => {
    expect(relativeTime('nope', tz, now)).toBe('');
    expect(relativeTime('2026-10-25T17:05:00Z', tz, now)).toBe('ahora');
  });
});
