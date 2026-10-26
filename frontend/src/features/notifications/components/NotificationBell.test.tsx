import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider, focusManager } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

vi.mock('../api', () => ({ notificationsApi: { list: vi.fn() } }));
import { notificationsApi } from '../api';
import { NotificationBell } from './NotificationBell';

const api = vi.mocked(notificationsApi);
const withUnread = (n: number) => ({ items: [], total: 0, page: 1, page_size: 1, unread_count: n });

function renderBell() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <NotificationBell />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('NotificationBell', () => {
  beforeEach(() => vi.clearAllMocks());

  it('muestra el contador y lo anuncia en el aria-label; enlaza a /avisos', async () => {
    api.list.mockResolvedValue(withUnread(2));
    renderBell();
    const link = await screen.findByRole('link', { name: 'Avisos, 2 sin leer' });
    expect(link).toHaveAttribute('href', '/avisos');
    expect(link).toHaveTextContent('2');
  });

  it('sin no leídas no muestra badge', async () => {
    api.list.mockResolvedValue(withUnread(0));
    renderBell();
    const link = await screen.findByRole('link', { name: 'Avisos' });
    expect(link).toHaveTextContent('');
  });

  it('pide solo las no leídas (page_size 1) y se refresca al enfocar la ventana', async () => {
    api.list.mockResolvedValue(withUnread(1));
    renderBell();
    await screen.findByRole('link', { name: 'Avisos, 1 sin leer' });
    expect(api.list).toHaveBeenCalledWith(1, true);
    api.list.mockResolvedValue(withUnread(3));
    act(() => {
      focusManager.setFocused(false);
      focusManager.setFocused(true);
    });
    expect(await screen.findByRole('link', { name: 'Avisos, 3 sin leer' })).toBeInTheDocument();
  });

  it('99+ para contadores grandes', async () => {
    api.list.mockResolvedValue(withUnread(120));
    renderBell();
    expect(await screen.findByText('99+')).toBeInTheDocument();
  });
});
