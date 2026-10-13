// Dashboard interface test + screenshots against the LOCAL server (run it on a copy of the event log).
//   VD_DASHBOARD_VAR=var/dashboard-uitest python -m director.dashboard.serve --port 8765 &
//   node tools/ui_dashboard_test.mjs http://127.0.0.1:8765 var/shots/dashboard
import { createRequire } from 'node:module';
import fs from 'node:fs';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PW_MODULE || '/opt/node22/lib/node_modules/playwright');
const [base, out] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
const res = []; const ok = (n, c, d = '') => res.push({ name: n, pass: !!c, detail: d }); const errors = []; const posts = [];
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args: ['--no-proxy-server'] });
async function open(w, h, scheme, hash = '') {
  const ctx = await b.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 2, colorScheme: scheme });
  await ctx.route((u) => !u.href.startsWith(base), (r) => r.abort());          // nothing leaves this machine
  const p = await ctx.newPage(); p.on('pageerror', (e) => errors.push(e.message));
  p.on('request', (r) => { if (r.method() !== 'GET') posts.push(r.method() + ' ' + new URL(r.url()).pathname); });
  await p.goto(base + '/' + hash); await p.waitForTimeout(500); return p;
}
const noScroll = (p) => p.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1);
const shot = (p, name, full = false) => p.screenshot({ path: `${out}/${name}.png`, fullPage: full });

// ---------------- phone, light
let p = await open(390, 844, 'light', '#dh~overview');
ok('overview: 7 stages', (await p.locator('.stage').count()) === 7);
ok('overview: stages approved shown as a count', /\d of 7/.test(await p.locator('.kpi').first().textContent()));
ok('overview: no percentage anywhere', !(/\d+(\.\d+)?\s?%/.test(await p.locator('main').textContent())));
ok('band shows the active profile', (await p.locator('#band').textContent()).includes('diabetes-history-sci'));
ok('phone: bottom tabs visible, rail hidden', (await p.locator('nav.tabs').isVisible()) && !(await p.locator('nav.rail').isVisible()));
ok('phone: no horizontal scroll (overview)', await noScroll(p));
await shot(p, 'm-overview');
await p.locator('.stages').scrollIntoViewIfNeeded(); await shot(p, 'm-overview-stages');
await p.goto(base + '/#dh~timeline'); await p.waitForTimeout(300);
ok('timeline: 20 scenes', (await p.locator('.sc').count()) === 20);
ok('timeline: segments proportional', await p.evaluate(() => { const a = [...document.querySelectorAll('.tl a')]; return a.length === 20 && a.every((x) => parseFloat(x.style.flexGrow) > 0); }));
ok('phone: no horizontal scroll (timeline)', await noScroll(p));
await shot(p, 'm-timeline');
await p.locator('.tl a').nth(7).click(); await p.waitForTimeout(400);
ok('timeline segment opens the scene', (await p.locator('main h2').textContent()).trim() === 'b1');
ok('scene: motion preview present', (await p.locator('.media video').count()) === 1);
ok('scene: technical and AI kept apart', (await p.locator('text=automated · measured').count()) === 1 && (await p.locator('text=AI judgement · not proof').count()) === 1);
await shot(p, 'm-scene-b1');
await p.locator('text=Artistic recommendations').scrollIntoViewIfNeeded(); await shot(p, 'm-scene-b1-findings');
await p.goto(base + '/#dh~gallery~b1'); await p.waitForTimeout(400);
ok('gallery: A/B/C versions for b1', (await p.locator('.ver img').count()) === 3);
ok('phone: no horizontal page scroll (gallery)', await noScroll(p));
await shot(p, 'm-gallery-b1');
await p.locator('.ver img').first().click(); await p.waitForTimeout(200);
ok('gallery: full-screen inspection', await p.locator('#lb').isVisible());
await shot(p, 'm-gallery-fullscreen'); await p.locator('#lbClose').click();
await p.goto(base + '/#tk~inbox~voice'); await p.waitForTimeout(300);
ok('inbox: Time Keeper voice items listed', (await p.locator('article.item').count()) >= 10);
ok('band switched to Time Keeper profile', (await p.locator('#band').textContent()).includes('timekeeper-luxury-doc'));
await shot(p, 'm-inbox-voice');
await p.goto(base + '/#dh~inbox~script'); await p.waitForTimeout(200);
ok('inbox: empty state for scripts', (await p.locator('.empty').count()) === 1);
await p.goto(base + '/#tk~costs'); await p.waitForTimeout(200);
ok('costs: ElevenLabs shown locked', (await p.locator('text=Locked').first().isVisible()));
await shot(p, 'm-costs');
await p.context().close();

// ---------------- phone, dark
p = await open(390, 844, 'dark', '#tk~timeline');
ok('Royal Oak: 36 scenes', (await p.locator('.sc').count()) === 36);
await shot(p, 'm-dark-tk-timeline');
await p.goto(base + '/#tk~identity'); await p.waitForTimeout(200);
ok('identity: separation checks all pass', (await p.locator('.check b').allTextContents()).every((t) => t === '✓'));
await shot(p, 'm-dark-identity');
await p.context().close();

// ---------------- desktop
p = await open(1366, 900, 'light', '#dh~overview');
ok('desktop: rail visible, tabs hidden', (await p.locator('nav.rail').isVisible()) && !(await p.locator('nav.tabs').isVisible()));
await shot(p, 'd-overview');
await p.goto(base + '/#dh~scene~b1'); await p.waitForTimeout(400); await shot(p, 'd-scene-b1');
await p.goto(base + '/#dh~gallery~b1'); await p.waitForTimeout(400); await shot(p, 'd-gallery-b1');
await p.goto(base + '/#dh~inbox'); await p.waitForTimeout(300); await shot(p, 'd-inbox');
await p.goto(base + '/#tk~costs'); await p.waitForTimeout(300); await shot(p, 'd-costs-tk');
await p.goto(base + '/#tk~overview'); await p.waitForTimeout(300); await shot(p, 'd-overview-tk');

// ---------------- decisions (on the test copy of the log)
const before = posts.length;
await p.goto(base + '/#dh~gallery~b1'); await p.waitForTimeout(300);
const c = p.locator('.ver').nth(2);
await c.locator('button[data-dec="approved"]').click(); await p.waitForTimeout(400);
ok('approve a version: it shows locked', (await p.locator('.ver').nth(2).locator('.lock').count()) >= 1);
ok('locked version: approve/reject disabled', await p.locator('.ver').nth(2).locator('button[data-dec="rejected"]').isDisabled());
ok('locked version: request changes still possible', !(await p.locator('.ver').nth(2).locator('button[data-dec="changes_requested"]').isDisabled()));
const r = await p.evaluate(async (u) => (await fetch(u + '/api/decision', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ item: 'ep7-b1-b1_v3', decision: 'rejected' }) })).status, base);
ok('server refuses to overwrite an approval (409)', r === 409, String(r));
await shot(p, 'd-gallery-b1-approved');
await p.goto(base + '/#tk~inbox~voice'); await p.waitForTimeout(300);
await p.locator('article.item').first().locator('button[data-dec="unsure"]').click(); await p.waitForTimeout(400);
ok('voice listening answer recorded', (await p.locator('article.item').first().textContent()).includes('Not sure'));
ok('only decision POSTs were sent', posts.slice(before).every((x) => x === 'POST /api/decision'), posts.slice(before).join(', '));
await p.goto(base + '/#tk~overview'); await p.waitForTimeout(300);
ok('overview voice stage counts the answer', /1 of 10/.test(await p.locator('.stage').nth(2).textContent()));
await p.context().close();
await b.close();

ok('no page errors', errors.length === 0, errors.join(' | '));
fs.writeFileSync(`${out}/results.json`, JSON.stringify(res, null, 1));
for (const x of res) console.log((x.pass ? 'PASS ' : 'FAIL ') + x.name + (x.detail ? '  (' + x.detail + ')' : ''));
const f = res.filter((x) => !x.pass).length; console.log(`${res.length - f}/${res.length} passed`); process.exit(f ? 1 : 0);
