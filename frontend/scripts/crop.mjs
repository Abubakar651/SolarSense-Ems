// Dev helper: crops the same region from a parity pair (design, port, diff), upscales, and stacks them.
import fs from 'node:fs';
import path from 'node:path';
import { PNG } from 'pngjs';

const [name, x, y, w = 60, h = 30, scale = 8] = process.argv.slice(2);
const dir = path.resolve(import.meta.dirname, '../parity-report');
const X = Number(x),
  Y = Number(y),
  W = Number(w),
  H = Number(h),
  S = Number(scale);
const read = (suffix) => PNG.sync.read(fs.readFileSync(path.join(dir, `${name}.${suffix}.png`)));
const imgs = ['a', 'b', 'diff'].map(read);
const out = new PNG({ width: W * S, height: H * S * 3 + 4 * 2 });
out.data.fill(255);
imgs.forEach((img, row) => {
  for (let yy = 0; yy < H * S; yy++) {
    for (let xx = 0; xx < W * S; xx++) {
      const sx = X + Math.floor(xx / S),
        sy = Y + Math.floor(yy / S);
      const si = (sy * img.width + sx) * 4;
      const di = ((row * (H * S + 4) + yy) * out.width + xx) * 4;
      out.data[di] = img.data[si];
      out.data[di + 1] = img.data[si + 1];
      out.data[di + 2] = img.data[si + 2];
      out.data[di + 3] = 255;
    }
  }
});
const file = path.join(dir, `crop-${name}.png`);
fs.writeFileSync(file, PNG.sync.write(out));
console.log(file);
