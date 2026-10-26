import { NavLink, Navigate, Outlet, useLocation } from 'react-router-dom';
import { ChartNoAxesColumn, CircleDot, Home, ListTodo, Plus, Target, type LucideIcon } from 'lucide-react';
import { useAuth } from '@/features/auth/AuthContext';
import { cn } from '@/shared/ui';

/** Contenedor mobile-first: ancho máx. 480px centrado en escritorio. */
export function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto flex h-dvh w-full max-w-[480px] flex-col overflow-hidden bg-bg md:border-x md:border-line">
      {children}
    </div>
  );
}

function NavItem({ to, label, icon: Icon, end }: { to: string; label: string; icon: LucideIcon; end?: boolean }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        cn(
          'flex min-h-[44px] flex-col items-center justify-center gap-1 text-[11px]',
          isActive ? 'font-semibold text-primary' : 'font-medium text-muted',
        )
      }
    >
      <Icon size={22} aria-hidden="true" />
      {label}
    </NavLink>
  );
}

export function BottomNav() {
  return (
    <nav
      aria-label="Navegación principal"
      className="grid h-[84px] shrink-0 grid-cols-5 items-center border-t border-[#E2E7E3] bg-surface px-2 pb-3 pb-safe"
    >
      <NavItem to="/" end label="Inicio" icon={Home} />
      <NavItem to="/movimientos" label="Movimientos" icon={ListTodo} />
      <NavLink
        to="/movimientos/nuevo"
        aria-label="Agregar movimiento"
        className="-mt-[18px] flex h-14 w-14 items-center justify-center justify-self-center rounded-[18px] bg-primary text-white shadow-[0_8px_20px_rgba(15,94,85,0.35)] hover:bg-primary-hover"
      >
        <Plus size={26} strokeWidth={2.4} aria-hidden="true" />
      </NavLink>
      <NavItem to="/reportes" label="Reportes" icon={ChartNoAxesColumn} />
      <NavItem to="/metas" label="Metas" icon={Target} />
    </nav>
  );
}

/** Rutas privadas con navegación inferior. */
export function AppLayout() {
  return (
    <Shell>
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
      <BottomNav />
    </Shell>
  );
}

/** Rutas privadas a pantalla completa (sin nav). */
export function FullScreenLayout() {
  return (
    <Shell>
      <main className="flex-1 overflow-y-auto bg-surface">
        <Outlet />
      </main>
    </Shell>
  );
}

export function RequireAuth() {
  const { status } = useAuth();
  const location = useLocation();
  if (status === 'loading') return <SplashScreen />;
  if (status === 'anonymous') return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  return <Outlet />;
}

export function SplashScreen() {
  return (
    <Shell>
      <div role="status" aria-label="Cargando" className="flex flex-1 items-center justify-center text-primary">
        <CircleDot size={32} className="animate-pulse" aria-hidden="true" />
      </div>
    </Shell>
  );
}
