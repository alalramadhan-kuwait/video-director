// UAT baseline probe: walk every tab of the CURRENT dashboard as a user who wants to start a new Time Keeper video.
//   node tools/uat_baseline_probe.mjs http://127.0.0.1:8767 OUT_DIR
import { createRequire } from 'node:module';
import fs from 'node:fs';
const require = createRequire(import.meta.url);
const { chromium, devices } = require('/opt/node22/lib/node_modules/playwright');
const [base, out] = process.argv.slice(2); fs.mkdirSync(out, { recursive: true });
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args: ['--no-proxy-server'] });
const iphone = { ...devices['iPhone 13'] }; delete iphone.defaultBrowserType;
const ctx = await b.newContext({ ...iphone, colorScheme: 'light' });
await ctx.route((u) => !u.href.startsWith(base), (r) => r.abort());
const p = await ctx.newPage(); const errors = []; p.on('pageerror', (e) => errors.push(e.message));
const rep = { tabs: {}, searches: {}, errors };
for (const h of ['tk~review', 'tk~scenes', 'tk~art', 'tk~style', 'tk~more', 'dh~review']) {
  await p.goto(base + '/#' + h); await p.waitForTimeout(700);
  await p.screenshot({ path: `${out}/${h.replace('~', '-')}.png`, fullPage: true });
  const txt = await p.evaluate(() => document.body.innerText);
  rep.tabs[h] = { buttons: await p.evaluate(() => [...document.querySelectorAll('button,a')].map((x) => x.innerText.trim()).filter(Boolean).slice(0, 60)) };
  for (const w of ['New project', 'Create', 'Script', 'Hook', 'Storyboard', 'Render', 'Research', 'Rolex', 'Authorize', 'ElevenLabs'])
    (rep.searches[w] ||= []).push(txt.toLowerCase().includes(w.toLowerCase()) ? h : null);
}
for (const w in rep.searches) rep.searches[w] = rep.searches[w].filter(Boolean);
// can the server create anything? (the only write is /api/decision)
const r = await fetch(base + '/api/project', { method: 'POST', body: '{}' }); rep.create_project_http = r.status;
fs.writeFileSync(`${out}/probe.json`, JSON.stringify(rep, null, 1)); console.log(JSON.stringify(rep.searches), rep.create_project_http, errors.length);
await b.close();
