import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { TransactionForm, pressKey } from './TransactionForm';
import type { Account } from '../../accounts/types';
import type { Category } from '../../categories/types';

const accounts: Account[] = [
  { id: 'a1', name: 'Nequi', type: 'wallet', initial_balance: '0.00', color: null, icon: null, archived: false, balance: '0.00', created_at: '' },
  { id: 'a2', name: 'Bancolombia', type: 'bank', initial_balance: '0.00', color: null, icon: null, archived: false, balance: '0.00', created_at: '' },
];
const categories: Category[] = [
  { id: 'c1', name: 'Comida', kind: 'expense', icon: 'utensils', color: '#0F5E55', parent_id: null },
  { id: 'c2', name: 'Salario', kind: 'income', icon: 'briefcase', color: '#1D4ED8', parent_id: null },
];

function setup() {
  const onSubmit = vi.fn();
  render(
    <MemoryRouter>
      <TransactionForm mode="create" accounts={accounts} categories={categories} today="2026-10-18" onSubmit={onSubmit} onCancel={() => {}} />
    </MemoryRouter>,
  );
  return { onSubmit, user: userEvent.setup() };
}

describe('TransactionForm', () => {
  it('pressKey respeta límite y ceros a la izquierda', () => {
    expect(pressKey('', '0')).toBe('');
    expect(pressKey('24', '5')).toBe('245');
    expect(pressKey('245', '⌫')).toBe('24');
    expect(pressKey('123456789012', '9')).toBe('123456789012');
  });

  it('valida: sin monto ni categoría no envía', async () => {
    const { onSubmit, user } = setup();
    await user.click(screen.getByRole('button', { name: 'Guardar movimiento' }));
    expect(await screen.findByText('Ingresa un monto mayor a 0')).toBeInTheDocument();
    expect(screen.getByText('Elige una categoría')).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('crea un gasto con teclado numérico y categoría', async () => {
    const { onSubmit, user } = setup();
    for (const k of ['2', '4', '5', '000']) await user.click(screen.getByRole('button', { name: k }));
    expect(screen.getByTestId('amount')).toHaveTextContent('− $ 245.000');
    await user.click(screen.getByRole('button', { name: /Comida/ }));
    await user.type(screen.getByLabelText('Nota'), 'Almuerzo');
    await user.click(screen.getByRole('button', { name: 'Guardar movimiento' }));
    expect(onSubmit).toHaveBeenCalledWith({
      type: 'expense',
      amount: '245000.00',
      date: '2026-10-18',
      account_id: 'a1',
      category_id: 'c1',
      transfer_account_id: null,
      note: 'Almuerzo',
    });
  });

  it('transferencia: exige cuenta destino distinta y no envía categoría', async () => {
    const { onSubmit, user } = setup();
    await user.click(screen.getByRole('button', { name: 'Transferir' }));
    expect(screen.queryByText('Categoría')).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: '5' }));
    await user.click(screen.getByRole('button', { name: 'Guardar movimiento' }));
    expect(await screen.findByText('Elige la cuenta destino')).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText('Hacia'), 'a2');
    await user.click(screen.getByRole('button', { name: 'Guardar movimiento' }));
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'transfer', amount: '5.00', account_id: 'a1', transfer_account_id: 'a2', category_id: null }),
    );
  });
});
