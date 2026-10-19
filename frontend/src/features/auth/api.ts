import { api, type TokenResponse } from '@/shared/api/client';
import type { User, UserUpdate } from './types';

export const authApi = {
  login: (email: string, password: string) =>
    api<TokenResponse>('/auth/login', { method: 'POST', body: { email, password }, auth: false }),
  logout: () => api<void>('/auth/logout', { method: 'POST', auth: false }),
  me: () => api<User>('/auth/me'),
  updateMe: (body: UserUpdate) => api<User>('/auth/me', { method: 'PATCH', body }),
  changePassword: (current_password: string, new_password: string) =>
    api<void>('/auth/change-password', { method: 'POST', body: { current_password, new_password } }),
};
