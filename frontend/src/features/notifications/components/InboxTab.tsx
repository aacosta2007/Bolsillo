import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell, CheckCheck } from 'lucide-react';
import { Button, EmptyState, ErrorState, ListSkeleton, cn } from '@/shared/ui';
import { useTimezone } from '@/features/auth/AuthContext';
import { useMarkAllRead, useMarkRead, useNotifications } from '../hooks';
import { relativeTime } from '../time';
import type { AppNotification } from '../types';
import { KIND_STYLE } from './kinds';

const PAGE = 30;

function Row({ n, tz, onOpen }: { n: AppNotification; tz: string; onOpen: (n: AppNotification) => void }) {
  const style = KIND_STYLE[n.kind] ?? KIND_STYLE.test;
  const Icon = style.icon;
  return (
    <li>
      <button
        type="button"
        onClick={() => onOpen(n)}
        className={cn(
          'flex w-full items-start gap-3 rounded-2xl border bg-surface px-3.5 py-3 text-left',
          n.read ? 'border-transparent' : 'border-[#F5D3AE]',
        )}
      >
        <span
          aria-hidden="true"
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[10px]"
          style={{ background: style.tint, color: style.ink }}
        >
          <Icon size={18} />
        </span>
        <span className="flex min-w-0 flex-1 flex-col gap-0.5">
          <span className="flex justify-between gap-2">
            <span className="text-sm font-bold">{n.title}</span>
            <span className="whitespace-nowrap text-[11px] text-muted">{relativeTime(n.created_at, tz)}</span>
          </span>
          <span className="text-[13px] leading-snug text-[#3D4843]">{n.body}</span>
        </span>
        {!n.read && <span role="img" aria-label="Sin leer" className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-[#C2410C]" />}
      </button>
    </li>
  );
}

export function InboxTab() {
  const tz = useTimezone();
  const navigate = useNavigate();
  const [size, setSize] = useState(PAGE);
  const q = useNotifications(size);
  const markRead = useMarkRead();
  const markAll = useMarkAllRead();

  if (q.isLoading) return <ListSkeleton rows={4} />;
  if (q.isError) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  const data = q.data;
  if (!data || data.items.length === 0) {
    return (
      <EmptyState
        icon={<Bell size={22} aria-hidden="true" />}
        title="Sin avisos por ahora"
        message="Aquí verás cuando un presupuesto se acerque a su límite, llegue tu quincena o tengas pagos próximos."
      />
    );
  }

  const open = (n: AppNotification) => {
    if (!n.read) markRead.mutate(n.id);
    if (n.url) navigate(n.url);
  };

  return (
    <div className="flex flex-col gap-3">
      {data.unread_count > 0 && (
        <Button variant="secondary" block loading={markAll.isPending} onClick={() => markAll.mutate()}>
          <CheckCheck size={16} aria-hidden="true" />
          Marcar todas como leídas
        </Button>
      )}
      <ul className="flex flex-col gap-2">
        {data.items.map((n) => (
          <Row key={n.id} n={n} tz={tz} onOpen={open} />
        ))}
      </ul>
      {data.total > data.items.length && (
        <Button variant="ghost" block onClick={() => setSize((s) => s + PAGE)}>
          Ver más
        </Button>
      )}
    </div>
  );
}
