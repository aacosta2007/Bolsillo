export const API_BASE = '/api/v1';

export class ApiError extends Error {
  status: number;
  detail: string;
  constructor(status: number, detail: string) {
    super(detail);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

// ---- Access token en memoria (nunca en localStorage) ----
let accessToken: string | null = null;
export const getAccessToken = () => accessToken;
export const setAccessToken = (t: string | null) => {
  accessToken = t;
};

let unauthorizedHandler: (() => void) | null = null;
/** Se invoca cuando la sesión no se pudo renovar (refresh falló). */
export const setUnauthorizedHandler = (fn: (() => void) | null) => {
  unauthorizedHandler = fn;
};

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

// ---- Refresh único: todas las peticiones concurrentes comparten la misma promesa ----
let refreshing: Promise<string | null> | null = null;

export function refreshAccessToken(): Promise<string | null> {
  if (!refreshing) {
    refreshing = (async () => {
      try {
        const res = await fetch(`${API_BASE}/auth/refresh`, { method: 'POST', credentials: 'include' });
        if (!res.ok) {
          accessToken = null;
          return null;
        }
        const data = (await res.json()) as TokenResponse;
        accessToken = data.access_token;
        return accessToken;
      } catch {
        accessToken = null;
        return null;
      } finally {
        refreshing = null;
      }
    })();
  }
  return refreshing;
}

type Query = Record<string, string | number | boolean | null | undefined>;

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';
  body?: unknown;
  query?: Query;
  /** false para login/refresh (no adjunta token ni reintenta). */
  auth?: boolean;
  signal?: AbortSignal;
}

function buildUrl(path: string, query?: Query) {
  const url = `${API_BASE}${path}`;
  if (!query) return url;
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) {
    if (v !== undefined && v !== null && v !== '') sp.set(k, String(v));
  }
  const qs = sp.toString();
  return qs ? `${url}?${qs}` : url;
}

async function errorFrom(res: Response): Promise<ApiError> {
  let detail = `Error ${res.status}`;
  try {
    const data = await res.json();
    if (typeof data?.detail === 'string') detail = data.detail;
    else if (Array.isArray(data?.detail)) {
      // Validación 422 de FastAPI
      detail = data.detail
        .map((d: { msg?: string; loc?: unknown[] }) => {
          const field = Array.isArray(d.loc) ? String(d.loc[d.loc.length - 1] ?? '') : '';
          return field ? `${field}: ${d.msg ?? 'inválido'}` : (d.msg ?? 'inválido');
        })
        .join('; ');
    }
  } catch {
    /* sin cuerpo JSON */
  }
  if (res.status === 429 && detail.startsWith('Error')) detail = 'Demasiados intentos. Espera unos minutos.';
  return new ApiError(res.status, detail);
}

async function doFetch(path: string, opts: RequestOptions): Promise<Response> {
  const { method = 'GET', body, query, auth = true, signal } = opts;
  const headers: Record<string, string> = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (auth && accessToken) headers.Authorization = `Bearer ${accessToken}`;
  return fetch(buildUrl(path, query), {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    credentials: 'include',
    signal,
  });
}

async function send(path: string, opts: RequestOptions): Promise<Response> {
  const auth = opts.auth ?? true;
  let res = await doFetch(path, opts);
  if (res.status === 401 && auth) {
    const token = await refreshAccessToken();
    if (token) {
      res = await doFetch(path, opts);
    } else {
      unauthorizedHandler?.();
    }
  }
  if (!res.ok) throw await errorFrom(res);
  return res;
}

export async function api<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const res = await send(path, opts);
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

export async function apiBlob(path: string, opts: RequestOptions = {}): Promise<{ blob: Blob; filename: string | null }> {
  const res = await send(path, opts);
  const cd = res.headers.get('Content-Disposition') ?? '';
  const m = /filename="?([^";]+)"?/i.exec(cd);
  return { blob: await res.blob(), filename: m?.[1] ?? null };
}
