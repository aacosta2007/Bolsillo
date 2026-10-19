import * as Tabs from '@radix-ui/react-tabs';
import { useSearchParams } from 'react-router-dom';
import { PageHeader } from '@/shared/ui';
import { RecurringTab } from '@/features/recurring/components/RecurringTab';
import { GoalsTab } from '../components/GoalsTab';

export function GoalsPage() {
  const [params, setParams] = useSearchParams();
  const tab = params.get('tab') === 'recurrentes' ? 'recurring' : 'goals';

  const trigger =
    'h-10 rounded-[10px] text-sm font-semibold text-muted data-[state=active]:bg-surface data-[state=active]:text-ink data-[state=active]:shadow-[0_1px_3px_rgba(22,32,27,0.15)]';

  return (
    <div className="flex flex-col gap-4 px-5 pb-6 pt-5">
      <PageHeader title="Metas" />
      <Tabs.Root
        value={tab}
        onValueChange={(v) => setParams(v === 'recurring' ? { tab: 'recurrentes' } : {}, { replace: true })}
        className="flex flex-col gap-4"
      >
        <Tabs.List aria-label="Secciones" className="grid grid-cols-2 gap-1 rounded-ctl2 bg-[#E7EBE7] p-1">
          <Tabs.Trigger value="goals" className={trigger}>
            Ahorro
          </Tabs.Trigger>
          <Tabs.Trigger value="recurring" className={trigger}>
            Recurrentes
          </Tabs.Trigger>
        </Tabs.List>
        <Tabs.Content value="goals">
          <GoalsTab />
        </Tabs.Content>
        <Tabs.Content value="recurring">
          <RecurringTab />
        </Tabs.Content>
      </Tabs.Root>
    </div>
  );
}
