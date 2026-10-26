import * as Tabs from '@radix-ui/react-tabs';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ChevronLeft } from 'lucide-react';
import { IconButton } from '@/shared/ui';
import { InboxTab } from '../components/InboxTab';
import { SettingsTab } from '../components/SettingsTab';

export function NotificationsPage() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const tab = params.get('tab') === 'configurar' ? 'configurar' : 'recientes';

  const trigger =
    'h-10 rounded-[10px] text-sm font-semibold text-muted data-[state=active]:bg-surface data-[state=active]:text-ink data-[state=active]:shadow-[0_1px_3px_rgba(22,32,27,0.15)]';

  return (
    <div className="flex flex-col gap-4 px-5 pb-6 pt-5">
      <header className="flex items-center gap-3">
        <IconButton label="Volver" onClick={() => navigate('/')}>
          <ChevronLeft size={20} aria-hidden="true" />
        </IconButton>
        <h1 className="font-display text-2xl font-bold">Avisos</h1>
      </header>
      <Tabs.Root
        value={tab}
        onValueChange={(v) => setParams(v === 'configurar' ? { tab: 'configurar' } : {}, { replace: true })}
        className="flex flex-col gap-4"
      >
        <Tabs.List aria-label="Sección" className="grid grid-cols-2 gap-1 rounded-ctl2 bg-[#E7EBE7] p-1">
          <Tabs.Trigger value="recientes" className={trigger}>
            Recientes
          </Tabs.Trigger>
          <Tabs.Trigger value="configurar" className={trigger}>
            Configurar
          </Tabs.Trigger>
        </Tabs.List>
        <Tabs.Content value="recientes">
          <InboxTab />
        </Tabs.Content>
        <Tabs.Content value="configurar">
          <SettingsTab />
        </Tabs.Content>
      </Tabs.Root>
    </div>
  );
}
