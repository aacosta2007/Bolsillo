import { formatMoney, formatPercent } from '@/shared/lib/money';
import type { DashboardSummary } from '../types';

export function BalanceCard({ data }: { data: DashboardSummary }) {
  const n = data.accounts.length;
  return (
    <section aria-label="Saldo total" className="flex flex-col gap-4 rounded-xl2 bg-primary p-5 text-white">
      <div className="flex flex-col gap-1">
        <span className="text-[13px] text-[#CFE6E1]">
          Saldo total · {n} {n === 1 ? 'cuenta' : 'cuentas'}
        </span>
        <span className="tnum font-display text-[36px] font-bold tracking-[-0.5px]">{formatMoney(data.total_balance)}</span>
      </div>
      <div className="grid grid-cols-3 gap-2">
        <Stat label="Ingresos" value={formatMoney(data.income)} />
        <Stat label="Gastos" value={formatMoney(data.expense)} />
        <Stat label="Ahorro" value={formatPercent(data.savings_rate)} />
      </div>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex min-w-0 flex-col gap-0.5 rounded-ctl2 bg-white/[0.12] p-2.5">
      <span className="text-xs text-[#CFE6E1]">{label}</span>
      <span className="tnum truncate text-[15px] font-bold">{value}</span>
    </div>
  );
}
