import { useCallback, useEffect, useState } from 'react';
import { errorMessage } from '@/shared/ui';
import { saveBlob } from '@/shared/lib/download';
import { reportsApi } from './api';

export const pdfFilename = (month: string) => `bolsillo_reporte_${month}.pdf`;

/** Descarga el PDF del mes (fetch autenticado → blob → archivo) y devuelve el File generado. */
export async function downloadMonthlyPdf(month: string): Promise<File> {
  const { blob, filename } = await reportsApi.monthlyPdf(month);
  const name = filename ?? pdfFilename(month);
  saveBlob(blob, name);
  return new File([blob], name, { type: 'application/pdf' });
}

/** ¿Puede el navegador compartir este archivo (Android/iOS con Web Share nivel 2)? */
export function canShareFile(file: File): boolean {
  try {
    return typeof navigator !== 'undefined' && typeof navigator.share === 'function' && !!navigator.canShare?.({ files: [file] });
  } catch {
    return false;
  }
}

export function useMonthlyPdf(month: string) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);

  useEffect(() => {
    setFile(null);
    setError(null);
  }, [month]);

  const download = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setFile(await downloadMonthlyPdf(month));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setLoading(false);
    }
  }, [month]);

  const share = useCallback(async () => {
    if (!file) return;
    try {
      await navigator.share({ files: [file], title: `Reporte ${month}` });
    } catch (e) {
      if (!(e instanceof DOMException && e.name === 'AbortError')) setError('No pudimos compartir el archivo.');
    }
  }, [file, month]);

  return { download, share, loading, error, canShare: file !== null && canShareFile(file) };
}
