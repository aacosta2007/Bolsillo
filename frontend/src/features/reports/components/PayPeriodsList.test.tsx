import { describe, expect, it } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { PayPeriodsList, formatNet } from './PayPeriodsList';
import { makePeriod } from '../fixtures';

describe('formatNet', () => {
  it('signos', () => {
    expect(formatNet('97900.00')).toBe('+ $ 97.900');
    expect(formatNet('-80000.00')).toBe('− $ 80.000');
    expect(formatNet('0.00')).toBe('$ 0');
  });
});

describe('PayPeriodsList', () => {
  it('muestra rango, meta, neto con signo y chip de estado', () => {
    render(
      <PayPeriodsList
        periods={[
          makePeriod(),
          makePeriod({ start: '2026-09-30', end: '2026-10-14', in_progress: false, days_elapsed: 15, days_remaining: 0, income: '1000000.00', expense: '902100.00', net: '97900.00', spent_per_day: '60140.00', status: 'justo' }),
          makePeriod({ start: '2026-08-14', end: '2026-08-30', days: 17, in_progress: false, income: '1000000.00', expense: '1080000.00', net: '-80000.00', spent_per_day: '63529.41', status: 'deficit' }),
          makePeriod({ start: '2026-09-15', end: '2026-09-29', in_progress: false, net: '230000.00', status: 'ahorro' }),
        ]}
      />,
    );
    const rows = screen.getAllByRole('listitem');
    expect(rows).toHaveLength(4);
    expect(within(rows[0]!).getByText('15 – 29 oct')).toBeInTheDocument();
    expect(within(rows[0]!).getByText(/día 6 de 15/)).toBeInTheDocument();
    expect(within(rows[0]!).getByText('+ $ 737.600')).toBeInTheDocument();
    expect(within(rows[0]!).getByText('en curso')).toBeInTheDocument();
    expect(within(rows[1]!).getByText('30 sep – 14 oct')).toBeInTheDocument();
    expect(within(rows[1]!).getByText('15 días · gastaste $ 902.100 · $ 60.140/día')).toBeInTheDocument();
    expect(within(rows[1]!).getByText('justo')).toBeInTheDocument();
    expect(within(rows[2]!).getByText('− $ 80.000')).toBeInTheDocument();
    expect(within(rows[2]!).getByText('déficit')).toBeInTheDocument();
    expect(within(rows[2]!).getByText(/17 días/)).toBeInTheDocument();
    expect(within(rows[3]!).getByText('ahorro')).toBeInTheDocument();
  });
});
