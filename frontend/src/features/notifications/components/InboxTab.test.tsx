import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import type { NotificationsPage } from '../types';

vi.mock('../api', () => ({
  notificationsApi: { list: vi.fn(), markRead: vi.fn().mockResolvedValue(undefined), markAllRead: vi.fn().mockResolvedValue(undefined) },
}));
vi.mock('@/features/auth/AuthContext', () => ({ useTimezone: () => 'America/Bogota' }));

import { notificationsApi } from '../api';
import { InboxTab } from './InboxTab';

const api = vi.mocked(notificationsApi);

const page = (over: Partial<NotificationsPage> = {}): NotificationsPage => ({
  items: [
    {
      id: 'n1',
      kind: 'budget_warning',
      title: 'Comida llegó al 85 %',
      body: 'Te quedan $ 90.000 de tu presupuesto para 11 días.',
      url: '/presupuestos',
      read: false,
      created_at: new Date(Date.now() - 2 * 3600_000).toISOString(),
    },
    { id: 'n2', kind: 'payday', title: 'Llegó tu quincena', body: 'Puedes gastar ≈ $ 66.600 por día', url: '/inicio-x', read: true, created_at: '2020-10-15T14:00:00Z' },
  ],
  total: 2,
  page: 1,
  page_size: 30,
  unread_count: 1,
  ...over,
});

function Where() {
  const l = useLocation();
  return <div data-testid="where">{l.pathname}</div>;
}

function renderInbox() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/avisos']}>
        <Routes>
          <Route path="/avisos" element={<InboxTab />} />
          <Route path="*" element={<Where />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('InboxTab', () => {
  beforeEach(() => vi.clearAllMocks());

  it('lista avisos con hora relativa y punto de no leída solo en los no leídos', async () => {
    api.list.mockResolvedValue(page());
    renderInbox();
    expect(await screen.findByText('Comida llegó al 85 %')).toBeInTheDocument();
    expect(screen.getByText('hace 2 h')).toBeInTheDocument();
    expect(screen.getAllByRole('img', { name: 'Sin leer' })).toHaveLength(1);
  });

  it('tocar un aviso no leído lo marca como leído y navega a su url', async () => {
    api.list.mockResolvedValue(page());
    renderInbox();
    await userEvent.click(await screen.findByRole('button', { name: /Comida llegó al 85 %/ }));
    await waitFor(() => expect(api.markRead.mock.calls[0]?.[0]).toBe('n1'));
    expect(await screen.findByTestId('where')).toHaveTextContent('/presupuestos');
  });

  it('tocar un aviso ya leído solo navega', async () => {
    api.list.mockResolvedValue(page());
    renderInbox();
    await userEvent.click(await screen.findByRole('button', { name: /Llegó tu quincena/ }));
    expect(await screen.findByTestId('where')).toHaveTextContent('/inicio-x');
    expect(api.markRead).not.toHaveBeenCalled();
  });

  it('"Marcar todas como leídas" llama al servidor', async () => {
    api.list.mockResolvedValue(page());
    renderInbox();
    await userEvent.click(await screen.findByRole('button', { name: 'Marcar todas como leídas' }));
    await waitFor(() => expect(api.markAllRead).toHaveBeenCalledOnce());
  });

  it('sin no leídas no muestra el botón de marcar todas', async () => {
    api.list.mockResolvedValue(page({ unread_count: 0 }));
    renderInbox();
    await screen.findByText('Comida llegó al 85 %');
    expect(screen.queryByRole('button', { name: 'Marcar todas como leídas' })).not.toBeInTheDocument();
  });

  it('estado vacío', async () => {
    api.list.mockResolvedValue(page({ items: [], total: 0, unread_count: 0 }));
    renderInbox();
    expect(await screen.findByText('Sin avisos por ahora')).toBeInTheDocument();
  });
});
