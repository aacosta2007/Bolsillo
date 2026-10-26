import { Bell, FileText, RefreshCw, TriangleAlert, Wallet, type LucideIcon } from 'lucide-react';
import type { NotificationKind } from '../types';

export const KIND_STYLE: Record<NotificationKind, { icon: LucideIcon; tint: string; ink: string }> = {
  budget_warning: { icon: TriangleAlert, tint: '#FFF0DC', ink: '#9A3412' },
  budget_exceeded: { icon: TriangleAlert, tint: '#FDECE2', ink: '#B33A0A' },
  upcoming_recurring: { icon: RefreshCw, tint: '#FDECE2', ink: '#9A3412' },
  payday: { icon: Wallet, tint: '#E4ECFD', ink: '#1D4ED8' },
  monthly_report: { icon: FileText, tint: '#E3F0ED', ink: '#0F5E55' },
  test: { icon: Bell, tint: '#E3F0ED', ink: '#0F5E55' },
};
