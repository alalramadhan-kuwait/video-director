// node tools/html_shot.mjs page.html out.jpg WIDTH HEIGHT  — screenshot a local HTML file (no network)
import { createRequire } from 'node:module';
import path from 'node:path';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PW_MODULE || '/opt/node22/lib/node_modules/playwright');
const [html, out, w, h] = process.argv.slice(2);
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
const ctx = await b.newContext({ viewport: { width: +w, height: +h }, deviceScaleFactor: 1 });
await ctx.route(/^https?:/, (r) => r.abort());
const p = await ctx.newPage();
await p.goto('file://' + path.resolve(html)); await p.waitForTimeout(150);
await p.screenshot({ path: out, type: out.endsWith('.png') ? 'png' : 'jpeg', ...(out.endsWith('.png') ? {} : { quality: 90 }) });
await b.close();
