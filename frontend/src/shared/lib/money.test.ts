import { describe, expect, it } from 'vitest';
import { digitsToAmount, formatMoney, formatPercent, formatSigned, parseUserAmount, percentOf, sumMoney } from './money';

describe('formatMoney', () => {
  it('formatea es-CO con puntos de miles', () => {
    expect(formatMoney('1234500.00')).toBe('$ 1.234.500');
    expect(formatMoney('0.00')).toBe('$ 0');
    expect(formatMoney('999.00')).toBe('$ 999');
    expect(formatMoney('4215300')).toBe('$ 4.215.300');
  });
  it('muestra decimales solo si existen', () => {
    expect(formatMoney('1250.50')).toBe('$ 1.250,50');
  });
  it('maneja negativos y montos enormes sin perder precisión', () => {
    expect(formatMoney('-90000.00')).toBe('− $ 90.000');
    expect(formatMoney('12345678901234.99')).toBe('$ 12.345.678.901.234,99');
  });
  it('signo por tipo', () => {
    expect(formatSigned('expense', '24500.00')).toBe('− $ 24.500');
    expect(formatSigned('income', '3500000.00')).toBe('+ $ 3.500.000');
    expect(formatSigned('transfer', '300000.00')).toBe('$ 300.000');
  });
});

describe('aritmética decimal', () => {
  it('suma sin errores de coma flotante', () => {
    expect(sumMoney(['0.10', '0.20'])).toBe('0.30');
    expect(sumMoney(['510000.00', '1200000.00', '145000.50'])).toBe('1855000.50');
  });
  it('porcentaje', () => {
    expect(percentOf('510000.00', '600000.00')).toBe(85);
    expect(percentOf('1.00', '0.00')).toBe(0);
  });
  it('teclado y entrada de usuario', () => {
    expect(digitsToAmount('24500')).toBe('24500.00');
    expect(digitsToAmount('')).toBe('0.00');
    expect(parseUserAmount('1.200.000')).toBe('1200000.00');
    expect(parseUserAmount('1200000,5')).toBe('1200000.50');
    expect(parseUserAmount('abc')).toBeNull();
  });
  it('porcentaje con coma', () => {
    expect(formatPercent(39.9)).toBe('39,9 %');
    expect(formatPercent(40)).toBe('40 %');
  });
});
