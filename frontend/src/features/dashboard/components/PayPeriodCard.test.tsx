import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { PaceNotice, PayPeriodCard } from './PayPeriodCard';
import { makePeriod } from '../../reports/fixtures';

const next = { date: '2026-10-30', amount: '1000000.00', note: 'Sueldo' };
const wrap = (ui: React.ReactElement) => render(<MemoryRouter>{ui}</MemoryRouter>);

describe('PayPeriodCard', () => {
  it('muestra el periodo en curso, disponible, por día y próximo pago', () => {
    wrap(<PayPeriodCard period={makePeriod()} nextPayday={next} />);
    expect(screen.getByText('Esta quincena · 15 – 29 oct')).toBeInTheDocument();
    expect(screen.getByText('Día 6 de 15')).toBeInTheDocument();
    expect(screen.getByText('Te quedan para 10 días')).toBeInTheDocument();
    expect(screen.getByText('$ 737.600')).toBeInTheDocument();
    expect(screen.getByText('$ 73.760 por día')).toBeInTheDocument();
    expect(screen.getByText(/hasta tu próximo pago \(vie 30 oct\)/)).toBeInTheDocument();
    expect(screen.getByText('Gastado 45 %')).toBeInTheDocument();
    expect(screen.getByText('Tiempo transcurrido 40 %')).toBeInTheDocument();
    expect(screen.getByText('$ 1.350.000')).toBeInTheDocument();
    expect(screen.getByText('$ 612.400')).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toHaveStyle({ width: '45.4%' });
    expect(screen.getByTestId('time-marker')).toHaveStyle({ left: '40%' });
    expect(screen.queryByText(/Marca tu sueldo/)).not.toBeInTheDocument();
  });

  it('con source calendar muestra "Quincena" y el enlace a recurrentes', () => {
    wrap(<PayPeriodCard period={makePeriod({ source: 'calendar', start: '2026-10-16', end: '2026-10-31' })} nextPayday={null} />);
    expect(screen.getByText('Quincena 16 – 31 oct')).toBeInTheDocument();
    const link = screen.getByRole('link', { name: 'Marca tu sueldo para medir de pago a pago' });
    expect(link).toHaveAttribute('href', '/metas?tab=recurrentes');
  });

  it('con net negativo muestra disponible $ 0', () => {
    wrap(
      <PayPeriodCard
        period={makePeriod({ net: '-120000.00', expense: '1470000.00', income: '1350000.00', available_per_day: '0.00', spent_percent: 108.9 })}
        nextPayday={next}
      />,
    );
    expect(screen.getByText('$ 0')).toBeInTheDocument();
    expect(screen.getByText('$ 0 por día')).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toHaveStyle({ width: '100%' });
  });
});

describe('PaceNotice', () => {
  it('avisa cuando el gasto va más rápido que el tiempo', () => {
    wrap(<PaceNotice period={makePeriod()} previous={makePeriod({ in_progress: false, spent_per_day: '61000.00' })} />);
    expect(screen.getByText('Vas un poco más rápido que el tiempo')).toBeInTheDocument();
    expect(screen.getByText(/La quincena pasada gastaste \$ 61\.000\/día; esta vas en \$ 102\.067\/día/)).toBeInTheDocument();
  });

  it('no avisa dentro del margen de 5 puntos y muestra mensaje positivo si va por debajo', () => {
    const { rerender } = wrap(<PaceNotice period={makePeriod({ spent_percent: 44, time_percent: 40 })} previous={null} />);
    expect(screen.queryByText(/más rápido/)).not.toBeInTheDocument();
    expect(screen.queryByText(/buen ritmo/)).not.toBeInTheDocument();
    rerender(
      <MemoryRouter>
        <PaceNotice period={makePeriod({ spent_percent: 30, time_percent: 40 })} previous={null} />
      </MemoryRouter>,
    );
    expect(screen.getByText(/buen ritmo/)).toBeInTheDocument();
  });
});
