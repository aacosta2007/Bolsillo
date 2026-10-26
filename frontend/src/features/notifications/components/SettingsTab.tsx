import { Button, Card, ErrorState, Field, ListSkeleton, Select, Switch, errorMessage } from '@/shared/ui';
import { usePreferences, useSendTest, useUpdatePreferences } from '../hooks';
import { PushBanner } from './PushBanner';

const hours = Array.from({ length: 24 }, (_, h) => h);
const days = Array.from({ length: 8 }, (_, d) => d);
const daysLabel = (d: number) => (d === 0 ? 'El mismo día' : d === 1 ? '1 día antes' : `${d} días antes`);

export function SettingsTab() {
  const q = usePreferences();
  const update = useUpdatePreferences();
  const test = useSendTest();

  return (
    <div className="flex flex-col gap-3">
      <PushBanner />

      {q.isLoading && <ListSkeleton rows={4} />}
      {q.isError && <ErrorState error={q.error} onRetry={() => q.refetch()} />}
      {q.data && (
        <>
          <Card className="flex flex-col divide-y divide-line px-4 py-1">
            <div className="py-2">
              <Switch
                label="Presupuestos"
                description="Cuando una categoría llega al umbral o se excede"
                checked={q.data.budget_alerts}
                onChange={(v) => update.mutate({ budget_alerts: v })}
              />
              {q.data.budget_alerts && (
                <p className="pb-1 text-xs text-muted">Umbral informativo: según cada presupuesto (80 % por defecto).</p>
              )}
            </div>
            <div className="py-2">
              <Switch
                label="Recurrentes próximos"
                description="Arriendo, servicios, suscripciones…"
                checked={q.data.upcoming_alerts}
                onChange={(v) => update.mutate({ upcoming_alerts: v })}
              />
              {q.data.upcoming_alerts && (
                <div className="grid grid-cols-2 gap-2 pb-2">
                  <Field label="Avisar">
                    {(p) => (
                      <Select
                        {...p}
                        value={q.data.upcoming_days_before}
                        onChange={(e) => update.mutate({ upcoming_days_before: Number(e.target.value) })}
                      >
                        {days.map((d) => (
                          <option key={d} value={d}>
                            {daysLabel(d)}
                          </option>
                        ))}
                      </Select>
                    )}
                  </Field>
                  <Field label="Hora">
                    {(p) => (
                      <Select {...p} value={q.data.notify_hour} onChange={(e) => update.mutate({ notify_hour: Number(e.target.value) })}>
                        {hours.map((h) => (
                          <option key={h} value={h}>
                            {String(h).padStart(2, '0')}:00
                          </option>
                        ))}
                      </Select>
                    )}
                  </Field>
                </div>
              )}
            </div>
            <div className="py-2">
              <Switch
                label="Llegó la quincena"
                description="Con tu presupuesto diario sugerido"
                checked={q.data.payday_alerts}
                onChange={(v) => update.mutate({ payday_alerts: v })}
              />
            </div>
            <div className="py-2">
              <Switch
                label="Reporte mensual"
                description="El día 1, cuando el mes anterior está listo"
                checked={q.data.monthly_report_alerts}
                onChange={(v) => update.mutate({ monthly_report_alerts: v })}
              />
            </div>
          </Card>
          {update.isError && (
            <p role="alert" className="text-xs text-expense">
              No se pudo guardar: {errorMessage(update.error)}
            </p>
          )}
        </>
      )}

      <Button variant="secondary" className="border-primary text-primary" loading={test.isPending} onClick={() => test.mutate()}>
        Enviar aviso de prueba
      </Button>
      <div role="status" aria-live="polite">
        {test.isSuccess && (
          <p className="text-sm text-muted">
            {test.data.sent > 0
              ? `Aviso de prueba enviado a ${test.data.sent} ${test.data.sent === 1 ? 'dispositivo' : 'dispositivos'}.`
              : 'Se creó el aviso de prueba en Recientes, pero no hay ningún celular con avisos activos.'}
            {test.data.failed > 0 && ` Falló en ${test.data.failed}.`}
          </p>
        )}
        {test.isError && <p className="text-sm text-expense">No se pudo enviar: {errorMessage(test.error)}</p>}
      </div>
      <p className="px-1 text-xs leading-snug text-muted">
        Los avisos viajan cifrados por el servicio de notificaciones de Chrome; nadie más puede leer su contenido. Al tocarlos se abre Bolsillo
        (necesitas Tailscale activo).
      </p>
    </div>
  );
}
