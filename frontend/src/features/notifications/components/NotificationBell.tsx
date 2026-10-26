import { Link } from 'react-router-dom';
import { Bell } from 'lucide-react';
import { useUnreadCount } from '../hooks';

/** Campana del encabezado de Inicio con contador de no leídas. */
export function NotificationBell() {
  const { data: unread = 0 } = useUnreadCount();
  const label = unread > 0 ? `Avisos, ${unread} sin leer` : 'Avisos';
  return (
    <Link
      to="/avisos"
      aria-label={label}
      title="Avisos"
      className="relative flex h-11 w-11 shrink-0 items-center justify-center rounded-ctl2 border border-line bg-surface text-ink hover:bg-bg"
    >
      <Bell size={20} aria-hidden="true" />
      {unread > 0 && (
        <span
          aria-hidden="true"
          className="absolute -right-1 -top-1 flex h-5 min-w-[20px] items-center justify-center rounded-full border-2 border-bg bg-[#C2410C] px-1 text-[11px] font-bold text-white"
        >
          {unread > 99 ? '99+' : unread}
        </span>
      )}
    </Link>
  );
}
