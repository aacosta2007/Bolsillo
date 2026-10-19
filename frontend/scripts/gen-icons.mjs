// Genera los iconos PNG de la PWA (sin dependencias) a partir de formas simples.
// Uso: node scripts/gen-icons.mjs
import { deflateSync } from 'node:zlib';
import { writeFileSync, mkdirSync } from 'node:fs';

const GREEN = [0x0f, 0x5e, 0x55];
const WHITE = [255, 255, 255];
const TINT = [0xe3, 0xf0, 0xed];

function crc32(buf) {
  let c;
  const table = [];
  for (let n = 0; n < 256; n++) {
    c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    table[n] = c >>> 0;
  }
  let crc = 0xffffffff;
  for (const b of buf) crc = table[(crc ^ b) & 0xff] ^ (crc >>> 8);
  return (crc ^ 0xffffffff) >>> 0;
}
function chunk(type, data) {
  const len = Buffer.alloc(4);
  len.writeUInt32BE(data.length);
  const td = Buffer.concat([Buffer.from(type), data]);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(td));
  return Buffer.concat([len, td, crc]);
}

function sdRoundRect(x, y, cx, cy, hw, hh, r) {
  const qx = Math.abs(x - cx) - hw + r;
  const qy = Math.abs(y - cy) - hh + r;
  return Math.hypot(Math.max(qx, 0), Math.max(qy, 0)) + Math.min(Math.max(qx, qy), 0) - r;
}

function render(size, maskable) {
  const SS = 3;
  const raw = Buffer.alloc((size * 4 + 1) * size);
  // En maskable, el contenido se reduce al 80% central (zona segura).
  const k = maskable ? 0.78 : 1;
  for (let py = 0; py < size; py++) {
    raw[py * (size * 4 + 1)] = 0;
    for (let px = 0; px < size; px++) {
      let r = 0, g = 0, b = 0, a = 0;
      for (let sy = 0; sy < SS; sy++) {
        for (let sx = 0; sx < SS; sx++) {
          const x = (px + (sx + 0.5) / SS) / size;
          const y = (py + (sy + 0.5) / SS) / size;
          let col = null;
          const bg = maskable ? -1 : sdRoundRect(x, y, 0.5, 0.5, 0.5, 0.5, 0.22);
          if (maskable || bg <= 0) col = GREEN;
          if (col) {
            const u = (x - 0.5) / k + 0.5;
            const v = (y - 0.5) / k + 0.5;
            // moneda
            if (Math.hypot(u - 0.5, v - 0.34) <= 0.15) col = TINT;
            // bolsillo
            if (sdRoundRect(u, v, 0.5, 0.64, 0.27, 0.19, 0.09) <= 0) col = WHITE;
            // costura del bolsillo
            if (Math.abs(v - 0.55) < 0.012 && Math.abs(u - 0.5) < 0.17) col = GREEN;
            r += col[0]; g += col[1]; b += col[2]; a += 255;
          }
        }
      }
      const n = SS * SS;
      const i = py * (size * 4 + 1) + 1 + px * 4;
      const cov = a / 255;
      raw[i] = cov ? Math.round(r / cov) : 0;
      raw[i + 1] = cov ? Math.round(g / cov) : 0;
      raw[i + 2] = cov ? Math.round(b / cov) : 0;
      raw[i + 3] = Math.round(a / n);
    }
  }
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(size, 0);
  ihdr.writeUInt32BE(size, 4);
  ihdr[8] = 8; ihdr[9] = 6;
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk('IHDR', ihdr),
    chunk('IDAT', deflateSync(raw)),
    chunk('IEND', Buffer.alloc(0)),
  ]);
}

mkdirSync('public/icons', { recursive: true });
writeFileSync('public/icons/icon-192.png', render(192, false));
writeFileSync('public/icons/icon-512.png', render(512, false));
writeFileSync('public/icons/icon-maskable-512.png', render(512, true));
console.log('Iconos generados en public/icons');
