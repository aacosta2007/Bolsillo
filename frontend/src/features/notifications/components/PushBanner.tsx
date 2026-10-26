import type { ReactNode } from 'react';
import { BellOff, BellRing, Check, Info } from 'lucide-react';
import { Button } from '@/shared/ui';
import { usePush } from '../usePush';

const BADGE = 'flex h-9 w-9 shrink-0 items-center justify-center rounded-[10px]';

const PROBLEM: Record<'unsupported' | 'denied' | 'unavailable', { title: string; desc: string }> = {
  unsupported: {
    title: 'Este navegador no admite avisos push',
    desc: 'Los avisos seguirán apareciendo en la pestaña Recientes. En Android usa Chrome e instala Bolsillo en la pantalla de inicio.',
  },
  denied: {
    title: 'Los avisos están bloqueados',
    desc: 'Para activarlos: en Chrome toca el menú (⋮) → Ajustes → Configuración del sitio → Notificaciones, permite Bolsillo y vuelve aquí.',
  },
  unavailable: {
    title: 'El servidor no tiene avisos push configurados',
    desc: 'Tus avisos seguirán apareciendo en la pestaña Recientes.',
  },
};

export function PushBanner() {
  const { status, busy, error, enable, disable } = usePush();
  if (status === 'loading') return null;

  let body: ReactNode;
  if (status === 'active') {
    body = (
      <>
        <div className="flex items-center gap-3">
          <span aria-hidden="true" className={`${BADGE} bg-primary text-white`}>
            <Check size={18} />
          </span>
          <div className="flex flex-1 flex-col">
            <span className="text-sm font-bold text-primary-hover">Avisos activos en este celular</span>
            <span className="text-xs text-[#2F5E56]">Llegan aunque la app esté cerrada</span>
          </div>
        </div>
        <Button variant="secondary" loading={busy} onClick={disable}>
          Desactivar avisos en este celular
        </Button>
      </>
    );
  } else if (status === 'inactive') {
    body = (
      <>
        <div className="flex items-center gap-3">
          <span aria-hidden="true" className={`${BADGE} bg-primary text-white`}>
            <BellRing size={18} />
          </span>
          <div className="flex flex-1 flex-col">
            <span className="text-sm font-bold text-primary-hover">Recibe avisos en este celular</span>
            <span className="text-xs text-[#2F5E56]">Te avisamos aunque la app esté cerrada</span>
          </div>
        </div>
        <Button loading={busy} onClick={enable}>
          Activar avisos en este celular
        </Button>
      </>
    );
  } else {
    const text = PROBLEM[status];
    body = (
      <div className="flex items-start gap-3">
        <span aria-hidden="true" className={`${BADGE} bg-[#C2410C] text-white`}>
          {status === 'denied' ? <BellOff size={18} /> : <Info size={18} />}
        </span>
        <div className="flex flex-1 flex-col gap-0.5">
          <span className="text-sm font-bold text-[#7A2A08]">{text.title}</span>
          <span className="text-xs leading-snug text-[#8A4A26]">{text.desc}</span>
        </div>
      </div>
    );
  }

  const tone = status === 'active' || status === 'inactive' ? 'bg-primary-tint' : 'border border-[#F5D3AE] bg-[#FFF4E8]';
  return (
    <section aria-label="Estado de los avisos push" className={`flex flex-col gap-3 rounded-2xl p-3.5 ${tone}`}>
      {body}
      {error && (
        <p role="alert" className="text-xs text-expense">
          {error}
        </p>
      )}
    </section>
  );
}
