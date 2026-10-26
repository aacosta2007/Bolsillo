import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { makeMonthlyReport } from '../fixtures';

vi.mock('../api', () => ({
  reportsApi: { monthly: vi.fn(), payPeriods: vi.fn(), monthlyPdf: vi.fn() },
}));
vi.mock('@/features/auth/AuthContext', () => ({ useTimezone: () => 'America/Bogota' }));
vi.mock('@/features/categories/hooks', () => ({
  useCategoryMap: () => ({
    map: new Map([
      ['c1', { id: 'c1', name: 'Comida' }],
      ['c2', { id: 'c2', name: 'Transporte' }],
    ]),
  }),
}));

import { reportsApi } from '../api';
import { MonthTab } from './MonthTab';

const api = vi.mocked(reportsApi);

function Where() {
  const l = useLocation();
  return <div data-testid="where">{l.search}</div>;
}

function renderTab(url = '/reportes?tab=mes&mes=2026-10') {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[url]}>
        <MonthTab />
        <Where />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('MonthTab', () => {
  beforeEach(() => {
    api.monthly.mockReset();
    api.monthly.mockResolvedValue(makeMonthlyReport());
  });

  it('muestra KPIs con variación, observaciones, categorías, ingresos, quincenas, presupuestos y metas', async () => {
    renderTab();
    expect(await screen.findAllByText('$ 2.350.000')).not.toHaveLength(0);
    expect(api.monthly).toHaveBeenCalledWith('2026-10');

    const kpis = screen.getByRole('region', { name: 'Resumen del mes' });
    expect(within(kpis).getByText(/subió 17,5 % frente a septiembre/)).toBeInTheDocument();
    expect(within(kpis).getByText(/subió 5,9 %/)).toBeInTheDocument();
    expect(within(kpis).getByText('28,3 %')).toBeInTheDocument();
    expect(within(kpis).getByText(/subió 7,8 puntos/)).toBeInTheDocument();
    // gasto que sube = naranja; ingreso que sube = verde
    expect(within(kpis).getByText('▲ 5,9 %').parentElement).toHaveClass('text-expense');
    expect(within(kpis).getByText('▲ 17,5 %').parentElement).toHaveClass('text-primary');

    const insights = screen.getByRole('region', { name: 'Lo que pasó en octubre' });
    expect(within(insights).getAllByRole('listitem')).toHaveLength(2);
    expect(within(insights).getByText(/18 % más en Comida/)).toBeInTheDocument();

    const cats = screen.getByRole('list', { name: 'Gasto por categoría' });
    const rows = within(cats).getAllByRole('listitem');
    expect(rows).toHaveLength(4);
    expect(within(rows[0]!).getByText('▲ 18 %').parentElement).toHaveClass('text-expense');
    expect(within(rows[1]!).getByText('▼ 20 %').parentElement).toHaveClass('text-primary');
    // categoría que bajó a 0
    expect(within(rows[2]!).getByText('Ocio')).toBeInTheDocument();
    expect(within(rows[2]!).getByText('$ 0')).toBeInTheDocument();
    expect(within(rows[2]!).getByText('▼ 100 %')).toBeInTheDocument();
    expect(within(rows[2]!).getByText(/bajó 100 %/)).toBeInTheDocument();
    expect(within(rows[3]!).getByText('= 0 %')).toBeInTheDocument();
    expect(screen.getByRole('img', { name: /Distribución del gasto: Comida 27 %/ })).toBeInTheDocument();

    const income = screen.getByRole('list', { name: 'Ingresos por fuente' });
    expect(within(income).getByText('nuevo')).toBeInTheDocument();
    expect(within(income).getByText('= 0 %')).toBeInTheDocument();

    expect(screen.getByText('Tus 5 gastos más grandes')).toBeInTheDocument();
    expect(screen.getByRole('img', { name: /Gasto día a día: 3 días/ })).toBeInTheDocument();
    expect(screen.getByText('Promedio diario')).toBeInTheDocument();
    expect(screen.getByText('$ 54.332')).toBeInTheDocument();

    const periods = screen.getByRole('list', { name: 'Quincenas del mes' });
    expect(within(periods).getByText('Sobraron $ 97.900')).toBeInTheDocument();
    expect(within(periods).getByText('Disponible $ 737.600')).toBeInTheDocument();

    expect(screen.getByText('3 cumplidos')).toBeInTheDocument();
    expect(screen.getByText('1 en riesgo')).toBeInTheDocument();
    expect(screen.getByText('1 excedido')).toBeInTheDocument();
    const budgets = screen.getByRole('list', { name: 'Presupuestos' });
    // los excedidos van primero
    expect(within(budgets).getAllByRole('listitem')[0]).toHaveTextContent('Comida');
    const goals = screen.getByRole('list', { name: 'Metas' });
    expect(within(goals).getByText('Vas bien')).toBeInTheDocument();
    expect(within(goals).getByText('Atrasada')).toBeInTheDocument();
    expect(within(goals).getByText(/aportaste \$ 300\.000/)).toBeInTheDocument();
    expect(within(goals).getByText(/sin aportes/)).toBeInTheDocument();
  });

  it('sin mes anterior: "sin datos del mes anterior"', async () => {
    const base = makeMonthlyReport();
    api.monthly.mockResolvedValue(
      makeMonthlyReport({
        summary: { ...base.summary, prev: null, income_change_pct: null, expense_change_pct: null, net_change_pct: null },
      }),
    );
    renderTab();
    expect(await screen.findAllByText('sin datos del mes anterior')).toHaveLength(4);
  });

  it('mes sin movimientos → estado vacío', async () => {
    const base = makeMonthlyReport();
    api.monthly.mockResolvedValue(
      makeMonthlyReport({
        summary: { ...base.summary, income: '0.00', expense: '0.00', net: '0.00' },
        expense_by_category: [],
        income_by_category: [],
      }),
    );
    renderTab();
    expect(await screen.findByText('Sin movimientos en Octubre 2026')).toBeInTheDocument();
  });

  it('error con reintentar', async () => {
    api.monthly.mockRejectedValueOnce(new Error('boom'));
    renderTab();
    expect(await screen.findByRole('alert')).toHaveTextContent('boom');
    await userEvent.click(screen.getByRole('button', { name: 'Reintentar' }));
    expect(await screen.findByRole('region', { name: 'Resumen del mes' })).toBeInTheDocument();
  });

  it('muestra "parcial", el selector actualiza la URL y no deja avanzar al futuro', async () => {
    const cur = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Bogota', year: 'numeric', month: '2-digit' })
      .format(new Date())
      .slice(0, 7);
    api.monthly.mockResolvedValue(makeMonthlyReport({ month: cur, is_partial: true }));
    renderTab(`/reportes?tab=mes&mes=${cur}`);
    expect(await screen.findByText('Mes en curso · parcial')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Mes siguiente' })).toBeDisabled();
    await userEvent.click(screen.getByRole('button', { name: 'Mes anterior' }));
    await waitFor(() => expect(screen.getByTestId('where').textContent).toMatch(/^\?tab=mes&mes=\d{4}-\d{2}$/));
    expect(screen.getByTestId('where').textContent).not.toContain(cur);
  });
});
