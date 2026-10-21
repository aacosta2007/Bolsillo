import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RecurringFormSheet } from './RecurringFormSheet';
import type { RecurringRule } from '../types';

const create = vi.fn();
const update = vi.fn();

vi.mock('../api', () => ({
  recurringApi: {
    create: (b: unknown) => create(b),
    update: (id: string, b: unknown) => update(id, b),
    remove: vi.fn(),
  },
}));
vi.mock('@/features/auth/AuthContext', () => ({ useAuth: () => ({ user: { timezone: 'America/Bogota' } }) }));
vi.mock('../../accounts/hooks', () => {
  const data = [
    { id: 'a1', name: 'Bancolombia' },
    { id: 'a2', name: 'Nequi' },
  ];
  return { useAccounts: () => ({ data }) };
});
vi.mock('../../categories/hooks', () => {
  const data = [
    { id: 'c1', name: 'Comida', kind: 'expense' },
    { id: 'c2', name: 'Salario', kind: 'income' },
  ];
  return { useCategories: () => ({ data }) };
});

function setup(rule: RecurringRule | null = null) {
  const qc = new QueryClient({ defaultOptions: { mutations: { retry: false }, queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <RecurringFormSheet open onOpenChange={() => {}} rule={rule} />
    </QueryClientProvider>,
  );
  return userEvent.setup();
}

beforeEach(() => {
  create.mockReset().mockResolvedValue({});
  update.mockReset().mockResolvedValue({});
});

describe('RecurringFormSheet', () => {
  it('quincenal 15 y último: muestra el equivalente mensual y envía monthly_days', async () => {
    const user = setup();
    await user.click(screen.getByRole('button', { name: 'Ingreso' }));
    await user.type(screen.getByLabelText('Monto por pago'), '1000000');
    await user.click(screen.getByRole('button', { name: 'Quincenal · 15 y último' }));
    expect(screen.getByText(/≈ \$ 2\.000\.000 al mes/)).toBeInTheDocument();
    expect(screen.queryByLabelText('Cada cuántos')).not.toBeInTheDocument();

    await user.type(screen.getByLabelText('Nota'), 'Sueldo');
    await user.selectOptions(screen.getByLabelText('Categoría'), 'c2');
    await user.selectOptions(screen.getByLabelText('Cuenta'), 'a1');
    await user.click(screen.getByRole('switch', { name: /Es mi sueldo/ }));
    await user.click(screen.getByRole('switch', { name: /viernes antes/ }));
    await user.click(screen.getByRole('button', { name: 'Guardar' }));

    await waitFor(() => expect(create).toHaveBeenCalledTimes(1));
    expect(create.mock.calls[0]![0]).toMatchObject({
      type: 'income',
      amount: '1000000.00',
      frequency: 'monthly_days',
      days_of_month: '15,L',
      interval: 1,
      weekend_adjust: 'previous_business_day',
      is_paycheck: true,
      account_id: 'a1',
      category_id: 'c2',
    });
  });

  it('"Es mi sueldo" solo aparece en ingresos y se apaga al volver a gasto', async () => {
    const user = setup();
    expect(screen.queryByRole('switch', { name: /Es mi sueldo/ })).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Ingreso' }));
    await user.click(screen.getByRole('switch', { name: /Es mi sueldo/ }));
    await user.click(screen.getByRole('button', { name: 'Gasto' }));
    await user.click(screen.getByRole('button', { name: 'Ingreso' }));
    expect(screen.getByRole('switch', { name: /Es mi sueldo/ })).toHaveAttribute('aria-checked', 'false');
  });

  it('días del mes: ordena con L al final y limita a 3', async () => {
    const user = setup();
    await user.type(screen.getByLabelText('Monto por pago'), '100000');
    await user.click(screen.getByRole('button', { name: 'Días del mes…' }));
    for (const n of ['Último día del mes', 'Día 20', 'Día 5', 'Día 9']) await user.click(screen.getByRole('button', { name: n }));
    expect(screen.getByRole('button', { name: 'Día 9' })).toHaveAttribute('aria-pressed', 'false');
    await user.selectOptions(screen.getByLabelText('Categoría'), 'c1');
    await user.selectOptions(screen.getByLabelText('Cuenta'), 'a1');
    await user.click(screen.getByRole('button', { name: 'Guardar' }));
    await waitFor(() => expect(create).toHaveBeenCalled());
    expect(create.mock.calls[0]![0]).toMatchObject({ frequency: 'monthly_days', days_of_month: '5,20,L', interval: 1, is_paycheck: false });
  });

  it('al editar preselecciona el chip y marca los pagos que se adelantan', () => {
    setup({
      id: 'r1',
      type: 'income',
      amount: '1000000.00',
      account_id: 'a1',
      category_id: 'c2',
      note: 'Sueldo',
      frequency: 'monthly_days',
      interval: 1,
      days_of_month: '15,30',
      weekend_adjust: 'previous_business_day',
      is_paycheck: true,
      start_date: '2099-10-01',
      end_date: null,
      next_run_date: '2099-10-15',
      active: true,
      monthly_equivalent: '2000000.00',
    });
    expect(screen.getByRole('button', { name: 'Quincenal · 15 y 30' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('switch', { name: /Es mi sueldo/ })).toHaveAttribute('aria-checked', 'true');
    expect(screen.getByText(/≈ \$ 2\.000\.000 al mes/)).toBeInTheDocument();
    expect(screen.getAllByText('cae fin de semana → se adelanta').length).toBeGreaterThan(0);
  });
});
