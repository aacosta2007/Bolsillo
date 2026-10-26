import * as Tabs from '@radix-ui/react-tabs';
import { useSearchParams } from 'react-router-dom';
import { PageHeader } from '@/shared/ui';
import { MonthTab } from '../components/MonthTab';
import { PayPeriodsTab } from '../components/PayPeriodsTab';

export function ReportsPage() {
  const [params, setParams] = useSearchParams();
  const tab = params.get('tab') === 'quincenas' ? 'quincenas' : 'mes';

  const trigger =
    'h-10 rounded-[10px] text-sm font-semibold text-muted data-[state=active]:bg-surface data-[state=active]:text-ink data-[state=active]:shadow-[0_1px_3px_rgba(22,32,27,0.15)]';

  return (
    <div className="flex flex-col gap-4 px-5 pb-6 pt-5">
      <PageHeader title="Reportes" />
      <Tabs.Root
        value={tab}
        onValueChange={(v) => setParams(v === 'quincenas' ? { tab: 'quincenas' } : {}, { replace: true })}
        className="flex flex-col gap-4"
      >
        <Tabs.List aria-label="Vista" className="grid grid-cols-2 gap-1 rounded-ctl2 bg-[#E7EBE7] p-1">
          <Tabs.Trigger value="mes" className={trigger}>
            Mes
          </Tabs.Trigger>
          <Tabs.Trigger value="quincenas" className={trigger}>
            Quincenas
          </Tabs.Trigger>
        </Tabs.List>
        <Tabs.Content value="mes">
          <MonthTab />
        </Tabs.Content>
        <Tabs.Content value="quincenas">
          <PayPeriodsTab />
        </Tabs.Content>
      </Tabs.Root>
    </div>
  );
}
