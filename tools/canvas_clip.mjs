// node tools/canvas_clip.mjs page.html "query" out_dir SECONDS FPS — render a canvas page that exposes
// window.draw(t) (a pure function of time) frame by frame to out_dir/f_00001.png. No network.
import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PW_MODULE || '/opt/node22/lib/node_modules/playwright');
const [html, query, out, secs, fps] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
const ctx = await b.newContext({ viewport: { width: 540, height: 960 }, deviceScaleFactor: 1 });
await ctx.route(/^https?:/, (r) => r.abort());
const p = await ctx.newPage(); const errs = []; p.on('pageerror', (e) => errs.push(e.message));
await p.goto('file://' + path.resolve(html) + '?' + query); await p.evaluate(() => window.ready);
const n = Math.round(+secs * +fps), c = p.locator('#c');
for (let i = 0; i < n; i++) {
  await p.evaluate((t) => window.draw(t), i / +fps);
  await c.screenshot({ path: path.join(out, `f_${String(i + 1).padStart(5, '0')}.png`) });
  if (process.send) process.send(i);
}
await b.close();
if (errs.length) { console.error(errs.join('\n')); process.exit(1); }
console.log(n, 'frames');
