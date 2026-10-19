import { z } from 'zod';
import { parseUserAmount, toCents } from './money';

/** Monto positivo escrito por una persona ("1.200.000", "50000,50"). */
export const positiveAmount = (message = 'Ingresa un monto mayor a 0') =>
  z.string().refine((v) => {
    const a = parseUserAmount(v);
    return a !== null && toCents(a) > 0n;
  }, message);

/** Monto >= 0 (saldo inicial). */
export const nonNegativeAmount = (message = 'Monto no válido') =>
  z.string().refine((v) => v.trim() === '' || parseUserAmount(v) !== null, message);

export const colorHex = z.string().regex(/^#[0-9a-fA-F]{6}$/, 'Color no válido');
