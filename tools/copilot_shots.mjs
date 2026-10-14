// node tools/copilot_shots.mjs BASE_URL PROJECT OUT_DIR [panels...] — iPhone-size screenshots of the Co-Pilot Studio,
// with a horizontal-overflow check per screen (the page must never scroll sideways on a phone).
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PW_MODULE || '/opt/node22/lib/node_modules/playwright');
const [base, pid, out, ...panels] = process.argv.slice(2);
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' });
const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
await ctx.route(/fonts\.(googleapis|gstatic)\.com/, r => r.abort());
const p = await ctx.newPage();
const errs = []; p.on('pageerror', e => errs.push(String(e)));
const res = {};
for (const pn of (panels.length ? panels : ['home', 'main', 'g1', 'g2', 'g3', 'g4', 'assets', 'scenes', 'scene/l9', 'g5', 'g6', 'inbox', 'ai', 'history'])) {
  const url = pn === 'home' ? `${base}/studio#/` : pn === 'main' ? `${base}/studio#/p/${pid}` : `${base}/studio#/p/${pid}/${pn}`;
  await p.goto(url); await p.waitForTimeout(1500);
  const ov = await p.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  res[pn] = { overflow_px: ov };
  await p.screenshot({ path: `${out}/${pn.replace('/', '-')}.png`, fullPage: true });
  await p.screenshot({ path: `${out}/v-${pn.replace('/', '-')}.png` });
}
console.log(JSON.stringify({ res, errors: errs }, null, 1));
await b.close();
