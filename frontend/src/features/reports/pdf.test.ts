import { afterEach, describe, expect, it, vi } from 'vitest';
import { downloadMonthlyPdf, pdfFilename } from './pdf';

function spyDownloads() {
  URL.createObjectURL = vi.fn(() => 'blob:x');
  URL.revokeObjectURL = vi.fn();
  const names: string[] = [];
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (this: HTMLAnchorElement) {
    names.push(this.download);
  });
  return names;
}

describe('descarga del PDF', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('pide el PDF autenticado y lo guarda con el nombre del servidor', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(new Blob(['%PDF-1.4'], { type: 'application/pdf' }), {
        status: 200,
        headers: { 'Content-Disposition': 'attachment; filename="bolsillo_reporte_2026-10.pdf"' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);
    const names = spyDownloads();

    const file = await downloadMonthlyPdf('2026-10');

    expect(fetchMock.mock.calls[0]![0]).toBe('/api/v1/reports/monthly/2026-10.pdf');
    expect(names).toEqual(['bolsillo_reporte_2026-10.pdf']);
    expect(file.name).toBe('bolsillo_reporte_2026-10.pdf');
    expect(file.type).toBe('application/pdf');
  });

  it('sin Content-Disposition usa el nombre por defecto', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(new Blob(['x']), { status: 200 })));
    const names = spyDownloads();
    await downloadMonthlyPdf('2026-09');
    expect(names).toEqual([pdfFilename('2026-09')]);
    expect(pdfFilename('2026-09')).toBe('bolsillo_reporte_2026-09.pdf');
  });

  it('propaga el error de la API', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: 'Mes futuro' }), { status: 400 })));
    await expect(downloadMonthlyPdf('2030-01')).rejects.toMatchObject({ detail: 'Mes futuro' });
  });
});
