// Interface test for the voice review page in real Chromium (no network: fonts may fall back, nothing else is fetched).
//   node tools/ui_voice_test.mjs var/pages/voice-royal-oak/index.html var/shots
// Exercises: queue shows 8 lines, word tap opens the sheet and seeks the audio to that word, listening answer is
// saved, mock take switch shows its warning, keep-Arabic correction updates the "if approved" total, verdict on an
// approved take shows the protection note. Writes phone/desktop screenshots in light and dark.
import { createRequire } from 'node:module';
import path from 'node:path';
import fs from 'node:fs';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PW_MODULE || '/opt/node22/lib/node_modules/playwright');

const [page_, outDir] = process.argv.slice(2);
const url = 'file://' + path.resolve(page_);
fs.mkdirSync(outDir, { recursive: true });
const results = [];
const ok = (name, cond, detail = '') => { results.push({ name, pass: !!cond, detail }); };

const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args: ['--autoplay-policy=no-user-gesture-required'] }).catch(() => chromium.launch());
const errors = [];
async function open(width, height, scheme) {
  const ctx = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: 2, colorScheme: scheme, hasTouch: width < 600 });
  await ctx.route(/^https?:/, (r) => r.abort());            // prove the page needs nothing from the network
  const p = await ctx.newPage();
  p.on('pageerror', (e) => errors.push(e.message));
  await p.goto(url); await p.waitForTimeout(400);
  return p;
}

// ---- phone, light: the queue
let p = await open(390, 844, 'light');
ok('queue lists 8 lines', (await p.locator('details.card').count()) === 8, String(await p.locator('details.card').count()));
ok('word sheet hidden on load', !(await p.locator('#pop').isVisible()));
ok('first queue line opens on load', (await p.locator('details.card[open]').count()) === 1);
ok('no horizontal scroll at 390px', await p.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
await p.screenshot({ path: `${outDir}/voice-phone-light-queue.png`, fullPage: false });

// open p2-1 and tap the target word
await p.locator('details.card[data-line="p2-1"] > summary').click(); await p.waitForTimeout(300);
const target = p.locator('details.card[data-line="p2-1"] .w.target').first();
ok('target word underlined in p2-1', (await target.count()) === 1 && (await target.textContent()).includes('الستيل'));
await target.click(); await p.waitForTimeout(500);
ok('word tap opens the mark sheet', await p.locator('#pop').isVisible());
const at = await p.evaluate(() => document.getElementById('au').currentTime);
const ws = +(await target.getAttribute('data-s'));
ok('word tap seeks the audio to the word', Math.abs(at - (ws - 0.2)) < 0.6, `audio at ${at.toFixed(2)}s, word starts ${ws}s`);
await p.screenshot({ path: `${outDir}/voice-phone-light-wordtap.png` });
await p.locator('#types button[data-t="الـ ناقصة"]').click();
await p.locator('#popSave').click(); await p.waitForTimeout(200);
ok('word sheet closes after saving', !(await p.locator('#pop').isVisible()));
ok('word mark saved and listed', (await p.locator('#marks .mk').count()) === 1);

// listening answer
await p.locator('details.card[data-line="p2-1"] .choice[data-q] button[data-v="unsure"]').click(); await p.waitForTimeout(200);
const saved = await p.evaluate(() => JSON.parse(localStorage.getItem('vr-royal-oak') || '{}'));
ok('listening answer saved', Object.values(saved.listening || {}).some((v) => v.line === 'p2-1' && v.heard === 'unsure'));

// verdict on the approved take shows the protection note
await p.locator('#vb-p2-1 .choice button[data-v="reject"]').click(); await p.waitForTimeout(200);
ok('reject of an approved take only records a decision', (await p.locator('#vn-p2-1').textContent()).includes('لا يحذفه'));

// correction → total
const before = await p.locator('#stats').textContent();
await p.locator('#corr-p2-1-keep_arabic').check();
await p.locator('details.card[data-line="p2-1"] button.primary', { hasText: 'احفظ الاقتراح' }).click(); await p.waitForTimeout(200);
const after = await p.locator('#stats').textContent();
ok('proposed correction updates the paid estimate', /161/.test(after) && after !== before, after);
await p.locator('details.card[data-line="p2-1"] .block').nth(2).scrollIntoViewIfNeeded();
await p.screenshot({ path: `${outDir}/voice-phone-light-correction.png` });

// mock take
await p.locator('details.card[data-line="p2-1"] .seg button', { hasText: 'mock' }).click(); await p.waitForTimeout(300);
ok('mock take shows its warning', await p.locator('#mock-p2-1').isVisible());
ok('mock audio is the mock file', (await p.evaluate(() => document.getElementById('au').getAttribute('src'))).endsWith('p2-1.mock.mp3'));
await p.locator('#mock-p2-1').scrollIntoViewIfNeeded();
await p.screenshot({ path: `${outDir}/voice-phone-light-mock.png` });

// all lines tab
await p.locator('#tabAll').click(); await p.waitForTimeout(200);
ok('all-lines tab lists 30', (await p.locator('details.card').count()) === 30);
await p.context().close();

// ---- phone, dark
p = await open(390, 844, 'dark');
await p.screenshot({ path: `${outDir}/voice-phone-dark-queue.png` });
ok('dark body background is dark', await p.evaluate(() => { const c = getComputedStyle(document.body).backgroundColor.match(/\d+/g).map(Number); return c[0] + c[1] + c[2] < 120; }));
await p.context().close();

// ---- desktop, light
p = await open(1280, 900, 'light');
await p.screenshot({ path: `${outDir}/voice-desktop-light.png` });
await p.context().close();
await browser.close();

ok('no page errors', errors.length === 0, errors.join(' | '));
fs.writeFileSync(`${outDir}/voice-ui-results.json`, JSON.stringify(results, null, 1));
for (const r of results) console.log((r.pass ? 'PASS ' : 'FAIL ') + r.name + (r.detail ? '  (' + r.detail + ')' : ''));
const failed = results.filter((r) => !r.pass).length;
console.log(`${results.length - failed}/${results.length} passed`);
process.exit(failed ? 1 : 0);
