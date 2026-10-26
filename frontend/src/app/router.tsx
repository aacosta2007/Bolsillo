import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AppLayout, FullScreenLayout, RequireAuth } from './layout';
import { LoginPage } from '@/features/auth/pages/LoginPage';
import { DashboardPage } from '@/features/dashboard/pages/DashboardPage';
import { TransactionsPage } from '@/features/transactions/pages/TransactionsPage';
import { TransactionFormPage } from '@/features/transactions/pages/TransactionFormPage';
import { BudgetsPage } from '@/features/budgets/pages/BudgetsPage';
import { ReportsPage } from '@/features/reports/pages/ReportsPage';
import { GoalsPage } from '@/features/goals/pages/GoalsPage';
import { SettingsPage } from '@/features/settings/pages/SettingsPage';

export const routes = [
  { path: '/login', element: <LoginPage /> },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { path: '/', element: <DashboardPage /> },
          { path: '/movimientos', element: <TransactionsPage /> },
          { path: '/presupuestos', element: <BudgetsPage /> },
          { path: '/reportes', element: <ReportsPage /> },
          { path: '/metas', element: <GoalsPage /> },
          { path: '/ajustes', element: <SettingsPage /> },
        ],
      },
      {
        element: <FullScreenLayout />,
        children: [
          { path: '/movimientos/nuevo', element: <TransactionFormPage /> },
          { path: '/movimientos/:id/editar', element: <TransactionFormPage /> },
        ],
      },
    ],
  },
  { path: '*', element: <Navigate to="/" replace /> },
];

export const router = () => createBrowserRouter(routes);
