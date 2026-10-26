import { Download, Share2 } from 'lucide-react';
import { Button } from '@/shared/ui';
import type { useMonthlyPdf } from '../pdf';

type Pdf = ReturnType<typeof useMonthlyPdf>;

/** Botón "PDF" del encabezado; "Compartir" aparece solo si el navegador puede compartir archivos. */
export function PdfButton({ pdf }: { pdf: Pdf }) {
  return (
    <>
      {pdf.canShare && (
        <Button variant="secondary" className="min-h-[44px] gap-2 px-3.5 text-sm font-bold" onClick={pdf.share} aria-label="Compartir PDF">
          <Share2 size={18} aria-hidden="true" />
          Compartir
        </Button>
      )}
      <Button className="min-h-[44px] gap-2 px-3.5 text-sm font-bold" onClick={pdf.download} loading={pdf.loading} aria-label="Descargar reporte en PDF">
        {!pdf.loading && <Download size={18} aria-hidden="true" />}
        {pdf.loading ? 'Generando…' : 'PDF'}
      </Button>
    </>
  );
}

export function PdfError({ pdf }: { pdf: Pdf }) {
  if (!pdf.error) return null;
  return (
    <p role="alert" className="rounded-ctl bg-expense-tint px-3 py-2 text-sm font-semibold text-expense">
      No pudimos generar el PDF: {pdf.error}
    </p>
  );
}
