import { describe, expect, it } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { MonthPeriods } from './MonthSections';
import { makeMonthlyReport, makePeriod } from '../fixtures';

describe('MonthPeriods', () => {
  it('neto negativo en palabras, "Sin gastos", sueldo/extra y chip calendario', () => {
    const report = makeMonthlyReport({
      pay_periods: [
        makePeriod({
          start: '2026-10-01', end: '2026-10-14', source: 'calendar', status: 'calendario', in_progress: false,
          days: 14, income: '0.00', salary_income: '0.00', extra_income: '0.00', expense: '0.00', net: '0.00',
          spent_per_day: '0.00', available_per_day: null,
        }),
        makePeriod({
          in_progress: false, days_remaining: 0, income: '1130000.00', salary_income: '930000.00',
          extra_income: '200000.00', expense: '1305900.00', net: '-175900.00', status: 'deficit',
        }),
        makePeriod({ start: '2026-10-30', end: '2026-11-14', income: '1000000.00', salary_income: '1000000.00', extra_income: '0.00', net: '700000.00' }),
      ],
    });
    render(<MonthPeriods report={report} monthName="octubre" />);
    const list = screen.getByRole('list', { name: 'Quincenas del mes' });
    const [cal, deficit, current] = within(list).getAllByRole('listitem');
    expect(within(cal!).getByText('calendario')).toBeInTheDocument();
    expect(within(cal!).getByText('Sin gastos')).toBeInTheDocument();
    expect(within(cal!).queryByText(/por día/)).not.toBeInTheDocument();
    expect(within(deficit!).getByText('Gastaste $ 175.900 más de lo que recibiste')).toBeInTheDocument();
    expect(within(deficit!).getByText('Sueldo $ 930.000 · Extra $ 200.000')).toBeInTheDocument();
    expect(within(deficit!).queryByText(/Disponible|Faltaron/)).not.toBeInTheDocument();
    expect(within(current!).getByText('Disponible $ 700.000')).toBeInTheDocument();
    expect(within(current!).getByText('Recibido $ 1.000.000')).toBeInTheDocument();
  });
});
