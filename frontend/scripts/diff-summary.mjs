// Dev helper: summarises parity-report diffs (count and bounding boxes of mismatching regions).
import fs from 'node:fs';
import path from 'node:path';
import { PNG } from 'pngjs';

const dir = path.resolve(import.meta.dirname, '../parity-report');
const only = process.argv[2];

for (const file of fs.readdirSync(dir).filter((f) => f.endsWith('.diff.png'))) {
  if (only && !file.includes(only)) continue;
  const img = PNG.sync.read(fs.readFileSync(path.join(dir, file)));
  const rows = new Map();
  let count = 0;
  for (let y = 0; y < img.height; y++) {
    for (let x = 0; x < img.width; x++) {
      const i = (y * img.width + x) * 4;
      if (img.data[i] > 200 && img.data[i + 1] < 90 && img.data[i + 2] < 90) {
        count++;
        const r = rows.get(y) ?? [x, x];
        r[0] = Math.min(r[0], x);
        r[1] = Math.max(r[1], x);
        rows.set(y, r);
      }
    }
  }
  // Merge consecutive rows into bands.
  const bands = [];
  for (const y of [...rows.keys()].sort((a, b) => a - b)) {
    const last = bands[bands.length - 1];
    const [x0, x1] = rows.get(y);
    if (last && y - last.y1 <= 3) {
      last.y1 = y;
      last.x0 = Math.min(last.x0, x0);
      last.x1 = Math.max(last.x1, x1);
    } else bands.push({ y0: y, y1: y, x0, x1 });
  }
  console.log(`${file}: ${count} px, ${bands.length} band(s)`);
  for (const b of bands.slice(0, 8)) console.log(`   y ${b.y0}-${b.y1}  x ${b.x0}-${b.x1}`);
}
