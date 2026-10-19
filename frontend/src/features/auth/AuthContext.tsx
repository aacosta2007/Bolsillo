import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { refreshAccessToken, setAccessToken, setUnauthorizedHandler } from '@/shared/api/client';
import { authApi } from './api';
import type { User } from './types';

type Status = 'loading' | 'authenticated' | 'anonymous';

interface AuthValue {
  status: Status;
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  setUser: (u: User) => void;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const [status, setStatus] = useState<Status>('loading');
  const [user, setUserState] = useState<User | null>(null);
  const booted = useRef(false);

  const clearSession = useCallback(() => {
    setAccessToken(null);
    setUserState(null);
    setStatus('anonymous');
    qc.clear();
  }, [qc]);

  // Restaurar sesión al abrir la app: la cookie de refresh es httpOnly.
  useEffect(() => {
    if (booted.current) return;
    booted.current = true;
    (async () => {
      const token = await refreshAccessToken();
      if (!token) return setStatus('anonymous');
      try {
        const me = await authApi.me();
        setUserState(me);
        setStatus('authenticated');
      } catch {
        setStatus('anonymous');
      }
    })();
  }, []);

  // Si un refresh falla durante el uso, volver al login.
  useEffect(() => {
    setUnauthorizedHandler(() => clearSession());
    return () => setUnauthorizedHandler(null);
  }, [clearSession]);

  const login = useCallback(
    async (email: string, password: string) => {
      const tokens = await authApi.login(email, password);
      setAccessToken(tokens.access_token);
      const me = await authApi.me();
      qc.clear();
      setUserState(me);
      setStatus('authenticated');
    },
    [qc],
  );

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      /* igual cerramos localmente */
    }
    clearSession();
  }, [clearSession]);

  const value = useMemo<AuthValue>(
    () => ({ status, user, login, logout, setUser: (u) => setUserState(u) }),
    [status, user, login, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth debe usarse dentro de AuthProvider');
  return ctx;
}

/** Zona horaria del usuario (por defecto America/Bogota). */
export function useTimezone(): string {
  return useAuth().user?.timezone ?? 'America/Bogota';
}
