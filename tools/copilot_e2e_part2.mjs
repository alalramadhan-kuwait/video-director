// Co-Pilot acceptance in a real browser (iPhone size), from an empty idea screen, against a fresh server.
//   node tools/copilot_e2e.mjs PORT VAR OUT
// The 12 scenarios run on one project in a realistic order (happy path first, then changes on top of it).
// Free tools only: the draft voice (Google TTS, free) and the local renderer; the AI is the MOCK worker (labelled).
// Results: OUT/results.json (PASS/FAIL per check with evidence) and screenshots in OUT/.
import { createRequire } from 'node:module';
import { execSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PW_MODULE || '/opt/node22/lib/node_modules/playwright');
const [PORT, VAR, OUT] = process.argv.slice(2);
const BASE = `http://127.0.0.1:${PORT}`;
const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
fs.mkdirSync(OUT, { recursive: true });
const R = []; let PID = process.env.PID;
const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a);
function ok(sc, name, pass, ev) { R.push({ scenario: sc, check: name, result: pass ? 'PASS' : 'FAIL', evidence: ev ?? null }); log(pass ? 'PASS' : 'FAIL', sc, name, ev != null ? JSON.stringify(ev).slice(0, 220) : '');
  fs.writeFileSync(`${OUT}/results-part2.json`, JSON.stringify({ pid: PID, results: R }, null, 1)); }
function server(cmd) { execSync(`${ROOT}/tools/copilot_server.sh ${cmd} ${PORT} ${VAR}`, { stdio: 'inherit' }); }
function killServer() { execSync(`ps -eo pid,comm,args | awk -v p="--port ${PORT}" '$2=="python3" && index($0,"dashboard.serve " p) {print $1}' | xargs -r kill -9`); }

const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args: ['--autoplay-policy=no-user-gesture-required'] });
const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
await ctx.route(/fonts\.(googleapis|gstatic)\.com/, r => r.abort());
const page = await ctx.newPage();
const errors = []; page.on('pageerror', e => errors.push(String(e)));
const toasts = [];
page.on('dialog', d => d.accept());
async function view() { const r = await ctx.request.get(`${BASE}/api/copilot/${PID}`); return r.json(); }
async function waitView(pred, label, mins = 20) {
  const t0 = Date.now(); let v;
  while (Date.now() - t0 < mins * 60e3) {
    try { v = await view(); if (pred(v)) { log('reached', label, Math.round((Date.now() - t0) / 1000) + 's'); return v; }
      if (v.blocked && v.blocked.length) { log('BLOCKED', JSON.stringify(v.blocked).slice(0, 300)); ok('run', `blocked while waiting for: ${label}`, false, v.blocked);
        throw new Error('stopped: a step is blocked (' + v.blocked[0].what + ')'); } } catch (e) { if (String(e).includes('stopped:')) throw e; }
    await page.waitForTimeout(3000);
  }
  log('TIMEOUT', label); ok('run', `timed out waiting for: ${label}`, false); throw new Error('stopped: timeout ' + label);
}
async function shot(name) { await page.screenshot({ path: `${OUT}/${name}.png` }); }
async function go(panel) {                            // wait until the page shows THIS screen, not the one before it
  await page.goto(`${BASE}/studio#/p/${encodeURIComponent(PID)}/${panel}`);
  await page.waitForFunction(() => document.querySelector('#main') && document.querySelector('#main').dataset.view === location.hash, null, { timeout: 30e3 });
  await page.waitForTimeout(300);
}
async function overflow() { return page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth); }
async function toastText() { const t = page.locator('#toast'); await page.waitForTimeout(400); return (await t.isVisible()) ? (await t.textContent()) : ''; }
async function playToEnd(sel, rate, maxS) {          // wait for THIS player's 'ended' (the page may redraw the panel after it stops)
  await page.evaluate(({ sel, rate }) => { const m = document.querySelector(sel); window.__ended = false; m.addEventListener('ended', () => { window.__ended = true; }, { once: true });
    m.currentTime = 0; m.playbackRate = rate; return m.play(); }, { sel, rate });
  await page.waitForFunction(() => window.__ended === true, null, { timeout: maxS * 1000, polling: 500 });
}
async function playRange(sel, a, b2, rate = 1) {
  await page.evaluate(({ sel, a, rate }) => { const m = document.querySelector(sel); m.currentTime = a; m.playbackRate = rate; return m.play(); }, { sel, a, rate });
  await page.waitForFunction(({ sel, b2 }) => { const m = document.querySelector(sel); return m.currentTime >= b2 || m.ended; }, { sel, b2 }, { timeout: 180e3, polling: 200 });
  await page.evaluate(sel => document.querySelector(sel).pause(), sel);
}
const gateBtn = (g, d) => page.locator(`[data-gate="${g}"][data-d="${d}"]`);
const filmScenes = v => (v.g5 && v.g5.scenes) || {};
const diff = (a, c) => Object.keys(c).filter(k => a[k] !== c[k]);

// ---- part 2: continue the same project from the scene that escalated (the first run's harness gave up 6 s too early)
try {
  let v = await view();
  let ex = v.exceptions.find(x => x.scene === 'l7' && x.status === 'open');
  ok('S5', 'a scene the Co-Pilot cannot fix safely stops and asks you (the Co-Pilot pauses)', !!ex && ex.kind === 'unfixable' && v.run === 'paused', ex);
  // the injected problem now has a fix that really changes this drawing: the correction-round path
  await ctx.request.post(`${BASE}/api/copilot/_test`, { data: { inject: { scene_review: { l7: [{ code: 'COMPOSITION', severity: 'major', detail: 'TEST: injected composition problem', detail_ar: 'مشكلة تكوين (اختبار)', fix: { slower: '1.4' } }] } } } });
  const l7before = v.scenes.find(s => s.id === 'l7').versions.length;
  await go('ex/' + ex.id); await shot('10-exception');
  await page.locator('[data-chip="text_size:1.2"]').click();
  await page.fill('#exnote', 'جرّب خطًا أكبر');
  await page.locator('[data-exd="retry_with_change"]').click(); await page.waitForTimeout(1500);
  v = await waitView(v => v.exceptions.some(x => x.scene === 'l7' && x.status === 'open' && x.id !== ex.id), 'l7 escalates again after its correction round', 30);
  const ex2 = v.exceptions.find(x => x.scene === 'l7' && x.status === 'open' && x.id !== ex.id);
  const l7 = v.scenes.find(s => s.id === 'l7');
  const tries = l7.versions.length - l7before;
  ok('S5', 'your change is tried, then a safe correction round, then it asks you again (never more than 2 rounds)', ex2 && ex2.kind === 'retry_limit' && tries >= 2 && tries <= 3 && l7.pick.rounds <= 2,
     { kind: ex2 && ex2.kind, tries, rounds: l7.pick.rounds, versions: l7.versions.map(x => [x.n, x.round, x.score, x.changes]) });
  ok('S5', 'every version and its evidence is kept', l7.versions.length === l7before + tries && l7.versions.every(x => x.still), l7.versions.length);
  await ctx.request.post(`${BASE}/api/copilot/_test`, { data: { inject: {} } });
  await go('ex/' + ex2.id);
  await page.fill('#exnote', 'مقبول كما هو في المسودة'); await page.locator('[data-exd="accept_best"]').click(); await page.waitForTimeout(1500);
  const f3 = filmScenes(await view());                 // film v3: the last film before the style change
  // ============================================================ S8 server interruption during the film render
  v = await waitView(v => v.task && /assemble|film/.test(v.task.what) && v.task.stage === 'film', 'film render running', 70);
  await page.waitForTimeout(20000);
  const before = await view();
  killServer(); log('server killed during', before.task && before.task.what);
  await page.waitForTimeout(3000);
  server('restart');
  v = await view();
  const resumed = v.runner_alive && v.task && v.task.stage === 'film';
  ok('S8', 'after the restart the interrupted render is recorded as interrupted and the film is started again by itself',
     resumed && (await (await ctx.request.get(`${BASE}/api/copilot/${PID}`)).json()).history.some(h => /interrupted|assemble/.test(h.summary)), { task: v.task, interrupted: v.interrupted });
  v = await waitView(v => v.g5 && v.waiting.includes('G5') && v.g5.films.some(f => f.state === 'ok' && f.n > 3), 'film after restart', 60);
  const dup = v.scenes.flatMap(s => s.versions.map(x => x.inputs).filter((h, i, a) => a.indexOf(h) !== i).map(h => s.id + ':' + h));
  ok('S8', 'the film completed after the interruption, nothing generated twice', v.waiting.includes('G5') && dup.length === 0, { films: v.g5.films, dup });
  ok('S4', 'after the style change every scene was redrawn in the new style', diff(f3, filmScenes(v)).length === 13, diff(f3, filmScenes(v)));
  const f4 = filmScenes(v);
  // ============================================================ S3 hook changed after narration
  const takesBefore = Object.fromEntries((await view()).g3.lines.map(l => [l.line, l.take]));
  await go('g2');
  await page.locator('[data-hook="H3"]').click(); await page.waitForTimeout(1500);
  v = await view();
  ok('S9', 'changing the hook outdates the script approval and the film', !v.validity.G2.valid && !v.validity.G5.valid, { G2: v.validity.G2, G5: v.validity.G5 });
  v = await waitView(v => v.waiting.includes('G2'), 'G2 for the new hook', 10);
  await go('g2');
  for (const c of await page.locator('[data-ack]').all()) await c.check();
  await gateBtn('G2', 'approved').click(); await page.waitForTimeout(1500);
  v = await waitView(v => v.waiting.includes('G3') && v.g3.mix_current, 'G3 after the hook', 15);
  const changedTakes = v.g3.lines.filter(l => l.take !== takesBefore[l.line]).map(l => l.line);
  ok('S3', 'only the hook line was voiced again; the other approved takes are untouched', JSON.stringify(changedTakes) === '["h"]', changedTakes);
  await go('g3');
  const seg = v.g3.mix.segments.find(s => s.line === 'h');
  await playRange('#mix', seg.start, seg.end + 0.1, 1);
  if (await page.locator('#ackqa').count()) await page.check('#ackqa');
  await gateBtn('G3', 'approved').click(); await page.waitForTimeout(1500);
  v = await view();
  ok('S3', 'Gate 3 needed only the changed line', v.validity.G3.valid, v.validity.G3);
  v = await waitView(v => v.g5 && v.waiting.includes('G5') && Object.keys(filmScenes(v)).length && diff(f4, filmScenes(v)).length > 0, 'film with the new hook', 60);
  ok('S3', 'only the opening scene was redone for the new hook', JSON.stringify(diff(f4, filmScenes(v))) === '["h"]', diff(f4, filmScenes(v)));
  ok('Reg', 'the new hook is the one rendered', !v.g5.findings.some(f => f.code === 'HOOK_MISMATCH'));
  // ============================================================ S12 draft played and reviewed on the phone, Gate 5
  await go('g5'); await shot('11-g5-final');
  ok('S12', 'no sideways scrolling on the film screen', (await overflow()) === 0);
  v = await view();
  for (const f of v.g5.findings.filter(f => !f.decision && (f.severity === 'critical' || f.severity === 'major'))) {
    if (f.severity === 'critical') ok('S12', 'no critical finding left at final review', false, [f.code, f.detail]);
    await page.fill(`[data-fexp="${f.id}"]`, f.severity === 'critical' ? 'TEST HARNESS: c8 records the swim; overruled only so the run can finish' : 'acceptable in this draft: reviewed by the owner on the phone');
    await page.locator(`[data-fdis="${f.id}"]`).click(); await page.waitForTimeout(1500);
  }
  await go('g5');
  const l5s = v.g5.timeline.find(s => s.id === 'l5');
  await playRange('#film', l5s.start + 0.3, l5s.start + 1.3, 1);
  ok('S12', 'the scene timeline follows the film', (await page.locator('#ftl button.on').getAttribute('data-sid').catch(() => null)) === 'l5');
  await playToEnd('#film', 2, 600);
  if (await page.locator('#ackminor').count()) await page.check('#ackminor');
  await gateBtn('G5', 'approved').click(); await page.waitForTimeout(2000);
  v = await view();
  ok('S1', 'Gate 5: you approved the complete draft', v.validity.G5.valid, v.validity.G5);
  // ============================================================ S11 paid calls
  v = await waitView(v => v.g6 && v.g6.plan, 'paid plan', 10);
  await go('g6'); await shot('12-g6');
  await page.fill('#g6c', String(v.g6.plan.chars_total)); await page.locator('[data-g6]').click(); await page.waitForTimeout(800);
  const t6 = await toastText();
  ok('S11', 'paid narration cannot be authorized here (blockers listed)', /not authorized|disabled/.test(t6), t6);
  const fg = await ctx.request.post(`${BASE}/api/copilot`, { data: { project: PID, action: 'final_generate', args: {} } });
  ok('S11', 'the page has no route to paid generation', fg.status() === 422);
  const g6o = await ctx.request.post(`${BASE}/api/copilot`, { data: { project: PID, action: 'cp_gate', args: { gate: 'G6', decision: 'approved', content_hash: 'old', confirm_text: '1' } } });
  ok('S11', 'an outdated paid approval is rejected', g6o.status() === 422, (await g6o.json()).reason);
  await ctx.request.post(`${BASE}/api/copilot`, { data: { project: PID, action: 'cp_settings', args: { worker: 'claude-code' } } });
  v = await view();
  ok('S11', 'the real AI worker has a $0 budget until you authorize one', v.ai.budget_usd === 0, v.ai);
  await ctx.request.post(`${BASE}/api/copilot`, { data: { project: PID, action: 'cp_settings', args: { worker: 'mock' } } });
  // ============================================================ S10 switch to Manual
  await go('');
  await page.locator('[data-manual]').click(); await page.waitForTimeout(1500);
  v = await view();
  ok('S10', 'switch to Manual: the Co-Pilot stops, every approval is kept', v.mode === 'manual' && v.run === 'stopped' && v.validity.G5.valid && v.validity.G3.valid, { mode: v.mode, run: v.run });
  await page.goto(`${BASE}/studio/classic#${PID}`); await page.waitForTimeout(2000); await shot('13-classic');
  ok('S10', 'the classic Studio opens the same project', (await page.content()).includes('Rolex Oyster'));
  // ============================================================ every screen on the phone
  await page.goto(`${BASE}/studio#/p/${PID}`); await page.waitForTimeout(1000);
  const ov = {};
  for (const p of ['', 'g1', 'g2', 'g3', 'g4', 'assets', 'scenes', 'scene/l9', 'g5', 'g6', 'inbox', 'ai', 'history']) { await go(p); ov[p || 'main'] = await overflow(); }
  ok('S12', 'no screen scrolls sideways on an iPhone-size screen', Object.values(ov).every(x => x === 0), ov);
  ok('S12', 'no script errors on the page', errors.length === 0, errors.slice(0, 5));
} catch (e) {
  ok('run', 'the scenario run finished', false, String(e && e.stack || e).slice(0, 800));
  await shot('zz-error').catch(() => {});
}
fs.writeFileSync(`${OUT}/results-part2.json`, JSON.stringify({ pid: PID, results: R, errors }, null, 1));
log('done', R.filter(r => r.result === 'PASS').length, 'pass', R.filter(r => r.result === 'FAIL').length, 'fail');
await b.close();
