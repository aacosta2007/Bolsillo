import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, api, getAccessToken, setAccessToken, setUnauthorizedHandler } from './client';

const json = (status: number, body?: unknown) =>
  new Response(body === undefined ? null : JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

let fetchMock: ReturnType<typeof vi.fn>;
beforeEach(() => {
  fetchMock = vi.fn();
  vi.stubGlobal('fetch', fetchMock);
  setAccessToken('old');
});
afterEach(() => {
  vi.unstubAllGlobals();
  setAccessToken(null);
  setUnauthorizedHandler(null);
});

describe('cliente API', () => {
  it('adjunta el token y usa la base /api/v1', async () => {
    fetchMock.mockResolvedValueOnce(json(200, { ok: 1 }));
    await api('/accounts', { query: { include_archived: false } });
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe('/api/v1/accounts?include_archived=false');
    expect(init.headers.Authorization).toBe('Bearer old');
  });

  it('ante 401 hace UN refresh y reintenta con el token nuevo', async () => {
    fetchMock
      .mockResolvedValueOnce(json(401, { detail: 'expirado' }))
      .mockResolvedValueOnce(json(200, { access_token: 'new', token_type: 'bearer', expires_in: 900 }))
      .mockResolvedValueOnce(json(200, { id: 1 }));
    const res = await api<{ id: number }>('/auth/me');
    expect(res).toEqual({ id: 1 });
    expect(fetchMock.mock.calls[1]![0]).toBe('/api/v1/auth/refresh');
    expect(fetchMock.mock.calls[1]![1].credentials).toBe('include');
    expect(fetchMock.mock.calls[2]![1].headers.Authorization).toBe('Bearer new');
    expect(getAccessToken()).toBe('new');
  });

  it('peticiones concurrentes con 401 comparten un único refresh', async () => {
    let refreshCalls = 0;
    fetchMock.mockImplementation(async (url: string, init: RequestInit & { headers: Record<string, string> }) => {
      if (url.endsWith('/auth/refresh')) {
        refreshCalls++;
        return json(200, { access_token: 'new', token_type: 'bearer', expires_in: 900 });
      }
      return init.headers.Authorization === 'Bearer new' ? json(200, { ok: true }) : json(401, { detail: 'x' });
    });
    await Promise.all([api('/a'), api('/b'), api('/c')]);
    expect(refreshCalls).toBe(1);
  });

  it('si el refresh falla limpia el token, avisa y lanza ApiError 401', async () => {
    const onUnauthorized = vi.fn();
    setUnauthorizedHandler(onUnauthorized);
    fetchMock.mockResolvedValueOnce(json(401, { detail: 'expirado' })).mockResolvedValueOnce(json(401, { detail: 'no' }));
    await expect(api('/auth/me')).rejects.toMatchObject({ status: 401 });
    expect(getAccessToken()).toBeNull();
    expect(onUnauthorized).toHaveBeenCalledTimes(1);
  });

  it('login (auth:false) no intenta refrescar y expone detail / 429', async () => {
    fetchMock.mockResolvedValueOnce(json(401, { detail: 'Credenciales inválidas' }));
    await expect(api('/auth/login', { method: 'POST', body: {}, auth: false })).rejects.toThrow('Credenciales inválidas');
    expect(fetchMock).toHaveBeenCalledTimes(1);

    fetchMock.mockResolvedValueOnce(json(429, { detail: 'Demasiados intentos' }));
    const err = (await api('/auth/login', { method: 'POST', body: {}, auth: false }).catch((e: unknown) => e)) as ApiError;
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(429);
  });

  it('formatea errores 422 de FastAPI y tolera 204', async () => {
    fetchMock.mockResolvedValueOnce(json(422, { detail: [{ loc: ['body', 'amount'], msg: 'valor inválido' }] }));
    await expect(api('/transactions', { method: 'POST', body: {} })).rejects.toThrow('amount: valor inválido');
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));
    await expect(api('/transactions/1', { method: 'DELETE' })).resolves.toBeUndefined();
  });
});
