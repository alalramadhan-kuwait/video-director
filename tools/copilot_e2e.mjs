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
const R = []; let PID = null;
const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a);
function ok(sc, name, pass, ev) { R.push({ scenario: sc, check: name, result: pass ? 'PASS' : 'FAIL', evidence: ev ?? null }); log(pass ? 'PASS' : 'FAIL', sc, name, ev != null ? JSON.stringify(ev).slice(0, 220) : '');
  fs.writeFileSync(`${OUT}/results.json`, JSON.stringify({ pid: PID, results: R }, null, 1)); }
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
async function overflow() {                          // page-level AND element-level: anything cut off at the screen edge counts
  return page.evaluate(() => {
    const W = document.documentElement.clientWidth;
    const scrolls = e => { for (let p = e.parentElement; p && p !== document.body && p !== document.documentElement; p = p.parentElement) { const o = getComputedStyle(p).overflowX; if (o === 'auto' || o === 'scroll' || o === 'hidden') return true; } return false; };
    const bad = [...document.querySelectorAll('#main *')].filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && (r.right > W + 1 || r.left < -1) && !scrolls(e); });
    const page = document.documentElement.scrollWidth - W;
    return page > 0 || bad.length ? { page, cut: bad.slice(0, 5).map(e => e.tagName + '.' + e.className + ' ' + (e.textContent || '').slice(0, 30)) , n: bad.length } : 0;
  });
}
async function closeToast() { const c = page.locator('#toast [data-tclose]'); if (await c.count() && await c.isVisible()) await c.click(); }
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
// The latest version is opened BEFORE listening or watching (go() loads it fresh); nothing is refreshed after playing.
// If the play-all changed while it played, the server refuses the decision (the listening was of another file) and the
// harness listens again, as an owner would; each replay is recorded in the results.
async function idleVoice() { return waitView(v => v.g3 && v.g3.mix_current && !(v.task && v.task.stage === 'voice'), 'voice idle, play-all current', 15); }
async function approveG3(play, label) {
  for (let i = 0; i < 3; i++) {
    let v = await view();
    if (v.validity.G3.valid) return v;
    if (i > 0) { const t = await toastText(); ok('run', `Gate 3 replay ${i} (${label}): the decision was refused, listening again`, true, t); await closeToast(); }
    v = await idleVoice(); await go('g3'); await play(v);
    if (await page.locator('#ackqa').count()) await page.check('#ackqa');
    await gateBtn('G3', 'approved').click(); await page.waitForTimeout(1500);
  }
  const v = await view(); ok(label, 'Gate 3 approved', v.validity.G3.valid, v.validity.G3); return v;
}
async function approveG5(sc) {
  let v = await view();
  for (const f of v.g5.findings.filter(f => !f.decision && (f.severity === 'critical' || f.severity === 'major'))) {
    if (f.severity === 'critical') ok(sc, 'no critical finding left at final review', false, [f.code, f.detail]);
    await go('g5');
    await page.fill(`[data-fexp="${f.id}"]`, f.severity === 'critical' ? 'TEST HARNESS: c8 records the swim; overruled only so the run can finish' : 'acceptable in this draft: reviewed by the owner on the phone');
    await page.locator(`[data-fdis="${f.id}"]`).click(); await page.waitForTimeout(1500);
  }
  await go('g5');
  await playToEnd('#film', 2, 600);
  if (await page.locator('#ackminor').count()) await page.check('#ackminor');
  await gateBtn('G5', 'approved').click(); await page.waitForTimeout(2000);
  return view();
}
const gateBtn = (g, d) => page.locator(`[data-gate="${g}"][data-d="${d}"]`);
const openAll = () => page.evaluate(() => document.querySelectorAll('#main details').forEach(d => { d.open = true; }));   // folded sections (more, other hooks…)
const filmScenes = v => (v.g5 && v.g5.scenes) || {};
const diff = (a, c) => Object.keys(c).filter(k => a[k] !== c[k]);

try {
  // ============================================================ S1 happy path, from an empty idea screen
  await page.goto(`${BASE}/studio`); await page.waitForTimeout(800);
  ok('S1', 'the guided Studio is the first screen (/ → /studio)', (await (await ctx.request.get(`${BASE}/`, { maxRedirects: 0 })).headers()['location']) === '/studio');
  await page.locator('button.primary.big').first().click(); await page.waitForTimeout(400);
  ok('S1', 'mode selector: Co-Pilot is the default, Auto is not available', await page.locator('input[value=copilot]').isChecked() && (await page.locator('input[value=auto]').count() === 0 || await page.locator('input[value=auto]').isDisabled()));
  await shot('01-new');
  await page.fill('#n-idea', 'كيف جعلت رولكس أويستر (1926) الناس يثقون بساعة في الماء — Rolex Oyster');
  await page.fill('#n-title', 'Rolex Oyster');
  await page.click('#n-go');
  await page.waitForFunction(() => location.hash.startsWith('#/p/'), null, { timeout: 30e3 });
  PID = decodeURIComponent(await page.evaluate(() => location.hash.split('/')[2]));
  let v = await waitView(v => v.waiting.includes('G1'), 'G1', 10);
  ok('S1', 'Co-Pilot did the research and waits at Gate 1 by itself', v.waiting.includes('G1'), { claims: v.g1 && v.g1.claims.length, mock: v.g1 && v.g1.mock });
  await go('g1');
  ok('S1', 'AI output is labelled MOCK on the screen', !!(v.g1 && v.g1.mock) && /(MOCK|تجريبي)/.test(await page.locator('.label-ai').first().textContent()));
  await go('g1'); await shot('02-g1');
  await gateBtn('G1', 'approved').click(); await page.waitForTimeout(1000);
  // ============================================================ S2 rejected script
  v = await waitView(v => v.waiting.includes('G2'), 'G2', 10);
  ok('S1', 'self-revision before Gate 2 (v1 → v2 by the AI)', v.g2.v === 2 && v.g2.versions[0].author === 'copilot', v.g2.versions);
  await go('g2'); await shot('03-g2');
  await page.locator('[data-open-note="G2"]').click();
  await page.fill('#note-G2', 'السطر الثاني طويل، اختصره');
  await gateBtn('G2', 'rejected').click(); await page.waitForTimeout(1000);
  v = await waitView(v => v.g2 && v.g2.v === 3 && v.waiting.includes('G2'), 'G2 after rejection', 10);
  ok('S2', 'rejected script → the AI revises it → a new version waits for you', v.g2.v === 3 && v.g2.versions.find(x => x.v === 2).status === 'rejected', v.g2.versions.map(x => [x.v, x.status]));
  ok('S2', 'the revision says honestly what the mock AI did', /MOCK AI/.test(v.g2.meta.why || ''), v.g2.meta.why);
  await go('g2');
  for (const c of await page.locator('[data-ack]').all()) await c.check();
  await gateBtn('G2', 'approved').click(); await page.waitForTimeout(1200);
  v = await view();
  ok('S1', 'only the approved version is used downstream', v.g2.approved_v === 3, v.g2.approved_v);
  // ============================================================ voice
  v = await waitView(v => v.waiting.includes('G3') && v.g3 && v.g3.mix_current, 'G3', 25);
  await go('g3'); await shot('04-g3');
  const dl = await page.locator('.label-draft').first().textContent();
  ok('S1', 'draft voice is labelled as free draft, not ElevenLabs', /(ليس|not)/i.test(dl) && /ElevenLabs/.test(dl) && /(تجريبي|draft|free|مجاني)/i.test(dl), dl);
  await page.locator('[data-gate="G3"][data-d="approved"]').click(); await page.waitForTimeout(800);
  ok('S1', 'Gate 3 refuses before the narration is heard', /(listen|استمع)/i.test(await toastText())); await closeToast();
  await playToEnd('#mix', 2, 300);
  await page.locator('.w').nth(3).click(); await page.waitForTimeout(800); await shot('05-g3-word');
  ok('S1', 'tapping a word opens its pronunciation / speed / compare sheet', await page.locator('.sheet').isVisible());
  const word = (await page.locator('.sheet b').first().textContent() || '').replace(/[«»]/g, '');
  const wline = (await page.locator('.sheet [data-line]').first().getAttribute('data-line') || '').trim();   // the line id (the screen shows its name)
  const nBefore = Object.fromEntries((await view()).g3.lines.map(l => [l.line, l.takes.length]));
  await page.fill('#respell', word + 'ْ'); await page.locator('[data-pron]').click(); await page.waitForTimeout(1500);
  v = await waitView(v => v.g3 && v.g3.mix_current && v.g3.lines.some(l => l.takes.length > nBefore[l.line]), 'new take after the pronunciation correction', 10);
  const reTaken = v.g3.lines.filter(l => l.takes.length > nBefore[l.line]).map(l => l.line);
  ok('S1', 'a pronunciation correction records only the corrected line again', JSON.stringify(reTaken) === JSON.stringify([wline]), { word, line: wline, reTaken });
  await idleVoice(); await go('g3');
  await playToEnd('#mix', 2, 300);                     // the narration changed: nothing is approved yet, so hear it all again
  v = await view();
  const nq = v.g3.qa.flags.filter(f => f.status === 'open').length;
  if (nq) {
    await page.locator('[data-seekmix]').first().click(); await page.waitForTimeout(2000);       // hear one of them as an owner would
      await gateBtn('G3', 'approved').click(); await page.waitForTimeout(800);
    const tq = await toastText();
    ok('S1', 'uncertain words must be confirmed before the voice is approved', /(uncertain|غير)/i.test(tq), nq);
    ok('S1', 'the refusal is in plain words: no internal ids', !/q-tk-|tk-[a-z0-9]+-/.test(tq), tq.slice(0, 160));
    await closeToast();
    await page.check('#ackqa');
  }
  await gateBtn('G3', 'approved').click(); await page.waitForTimeout(1500);
  v = await approveG3(async () => playToEnd('#mix', 2, 300), 'S1');
  ok('S1', 'voice approved after play-all: every line approved', v.validity.G3.valid, v.validity.G3);
  // ============================================================ style
  v = await waitView(v => v.waiting.includes('G4'), 'G4', 10);
  await go('g4'); await shot('06-g4');
  const boards = await page.evaluate(() => [...document.querySelectorAll('.board img')].map(i => ({ w: i.naturalWidth, src: i.src })));
  ok('S1', 'at least 3 styles with real, different boards that load', boards.length >= 3 && boards.every(b => b.w > 0) && new Set(boards.map(b => b.src)).size === boards.length,
     { boards: boards.length, recommended: v.g4.recommended });
  await gateBtn('G4', 'approved').click(); await page.waitForTimeout(1200);
  // ============================================================ scenes and film
  v = await waitView(v => v.scenes.length && v.task && v.task.stage === 'scenes', 'scenes running', 10);
  await go(''); await shot('07-working');
  ok('S1', 'scene progress and the current task are shown while the Co-Pilot works', !!v.task, v.task && v.task.what);
  v = await waitView(v => v.waiting.includes('G5'), 'G5 (film v1)', 50);
  ok('S1', 'a reviewed draft film waits at Gate 5 without any per-scene owner pause', v.waiting.includes('G5') && v.scenes.every(s => s.state === 'ai_reviewed'), v.scenes.map(s => [s.id, s.state]));
  await go('g5');
  ok('S1', 'scenes show as AI reviewed and the film as waiting for you, never as approved by you', (await page.locator('.timeline .tl-ai_reviewed').count()) >= 13
     && v.stages.find(s => s.id === 'film').state === 'needs_owner' && !v.validity.G5.valid, v.stages.find(s => s.id === 'film'));
  const f1 = filmScenes(v);
  ok('Reg', 'no critical finding in the happy-path film (the hook card question is not a claim)', !v.g5.findings.some(f => f.severity === 'critical'),
     v.g5.findings.filter(f => f.severity === 'critical').map(f => [f.code, f.scene, f.detail.slice(0, 80)]));
  ok('Reg', 'opening frame is not blank and the tail is not silent black', !v.g5.findings.some(f => ['OPENING_BLANK', 'SILENT_TAIL'].includes(f.code)), v.g5.findings.map(f => f.code));
  ok('Reg', 'the film opens with the approved hook', !v.g5.findings.some(f => f.code === 'HOOK_MISMATCH'));
  ok('Reg', 'no banner carried over between scenes', !v.g5.findings.some(f => f.code === 'BANNER_CARRIED_OVER'));
  await go('g5'); await shot('08-g5');
  // ============================================================ S7 targeted scene revision (a time-coded comment)
  const l9 = v.g5.timeline.find(s => s.id === 'l9');
  await page.evaluate(t => { const m = document.querySelector('#film'); m.currentTime = t; }, l9.start + 1.0); await page.waitForTimeout(500);
  await page.fill('#cm', 'الخط صغير هنا، كبّره'); await page.locator('[data-comment]').click(); await page.waitForTimeout(1500);
  v = await view();
  const cm = v.g5.comments[v.g5.comments.length - 1];
  ok('S7', 'a time-coded comment becomes a task on the scene playing then', cm && cm.scene === 'l9', cm);
  v = await waitView(v => v.g5 && v.g5.n >= 2 && v.waiting.includes('G5'), 'film v2', 45);
  ok('S7', 'only the commented scene was redone', JSON.stringify(diff(f1, filmScenes(v))) === '["l9"]', diff(f1, filmScenes(v)));
  const f2 = filmScenes(v);
  // ============================================================ S6 missing licensed picture
  await go('assets'); await shot('09-assets');
  await page.setInputFiles('#up-file', path.join(ROOT, 'vendor/paper-story/tk-logo-512.png'));
  await page.selectOption('#up-slot', { index: 0 });
  await page.fill('#up-credit', 'TEST PICTURE (not a real portrait) — e2e');
  await page.locator('[data-upload]').click(); await page.waitForTimeout(1500);
  v = await waitView(v => v.exceptions.some(x => x.kind === 'rights' && x.status === 'open'), 'rights exception', 5);
  ok('S6', 'a picture without licence evidence raises an exception and is not used', v.exceptions.some(x => x.kind === 'rights' && x.status === 'open')
     && v.assets.library[0].status === 'unverified', v.assets.library.map(a => [a.id, a.status]));
  await go('assets');
  await page.fill(`[data-licev="${v.assets.library[0].id}"]`, 'nonsense'); await page.locator(`[data-lic="${v.assets.library[0].id}"]`).click(); await page.waitForTimeout(800);
  ok('S6', 'a licence without evidence is refused', /(evidence|دليل)/i.test(await toastText())); await closeToast();
  await page.fill(`[data-licev="${v.assets.library[0].id}"]`, 'https://example.org/test-licence-page'); await page.locator(`[data-lic="${v.assets.library[0].id}"]`).click(); await page.waitForTimeout(1500);
  v = await waitView(v => v.g5 && v.g5.n >= 3 && v.waiting.includes('G5'), 'film v3 (licensed picture)', 45);
  const l6 = v.scenes.find(s => s.id === 'l6');
  ok('S6', 'with evidence the exception closes and only that scene uses the picture', v.exceptions.every(x => x.kind !== 'rights' || x.status !== 'open')
     && l6.pick.technique === 'archival_collage' && JSON.stringify(diff(f2, filmScenes(v))) === '["l6"]', { tech: l6.pick.technique, changed: diff(f2, filmScenes(v)) });
  const f3 = filmScenes(v);
  await go('assets');                                              // the test picture is not a real portrait: withdraw it (kept in the history)
  await ctx.request.post(`${BASE}/api/copilot`, { data: { project: PID, action: 'cp_asset', args: { op: 'withdraw', id: v.assets.library[0].id, note: 'test picture only' } } });
  // ============================================================ S5 + S4: a scene that keeps failing, during a style change
  await ctx.request.post(`${BASE}/api/copilot/_test`, { data: { inject: { scene_review: { l7: [{ code: 'COMPOSITION', severity: 'major', detail: 'TEST: injected composition problem', detail_ar: 'مشكلة تكوين (اختبار)', fix: { slower: '1.4' } }] } } } });   // a fix that really changes this drawing, but the problem stays
  await go('g4');
  await page.locator('[data-style="technical"]').click(); await page.waitForTimeout(500);
  await gateBtn('G4', 'approved').click(); await page.waitForTimeout(1500);
  v = await view();
  ok('S9', 'a style change outdates every scene drawn in the old style (and nothing is approved over it)',
     v.scenes.filter(s => s.state === 'outdated').length >= 12 && v.validity.G4.valid, v.scenes.map(s => s.state));
  const l7before = (v.scenes.find(s => s.id === 'l7').versions || []).length;
  v = await waitView(v => v.exceptions.some(x => x.scene === 'l7' && x.status === 'open'), 'l7 exception', 75);
  const ex = v.exceptions.find(x => x.scene === 'l7' && x.status === 'open');
  ok('S5', 'a scene still wrong after its safe correction round stops and asks you (the Co-Pilot pauses)', !!ex && ex.kind === 'retry_limit' && v.run === 'paused', ex);
  let l7 = v.scenes.find(s => s.id === 'l7');
  let tries = l7.versions.length - l7before;
  ok('S5', 'every version and its evidence is kept: at most 3 drawings (2 correction rounds) before asking you', tries >= 2 && tries <= 3 && l7.pick.rounds >= 1 && l7.pick.rounds <= 2,
     { tries, rounds: l7.pick.rounds, versions: l7.versions.map(x => [x.n, x.round, x.score, x.changes]) });
  await go('ex/' + ex.id); await shot('10-exception');
  await page.locator('[data-chip="text_size:1.2"]').click();                  // your own change: tried, then asks again
  await page.fill('#exnote', 'جرّب خطًا أكبر'); await page.locator('[data-exd="retry_with_change"]').click(); await page.waitForTimeout(1500);
  v = await waitView(v => v.exceptions.some(x => x.scene === 'l7' && x.status === 'open' && x.id !== ex.id), 'l7 asks again after your change', 30);
  const ex2 = v.exceptions.find(x => x.scene === 'l7' && x.status === 'open' && x.id !== ex.id);
  l7 = v.scenes.find(s => s.id === 'l7');
  ok('S5', 'your change is tried with its own correction round, then it asks you again', ex2 && ex2.kind === 'retry_limit' && l7.pick.rounds <= 2
     && l7.versions.some(x => x.changes && x.changes.slower), { kind: ex2 && ex2.kind, versions: l7.versions.map(x => [x.n, x.round, x.score, x.changes]) });
  await ctx.request.post(`${BASE}/api/copilot/_test`, { data: { inject: {} } });
  await go('ex/' + ex2.id);
  await page.fill('#exnote', 'مقبول كما هو في المسودة'); await page.locator('[data-exd="accept_best"]').click(); await page.waitForTimeout(1500);
  // ============================================================ S8 server interruption during the film render
  v = await waitView(v => v.task && /assemble|film/.test(v.task.what) && v.task.stage === 'film', 'film render running', 75);
  await page.waitForTimeout(20000);
  const before = await view();
  const cutN = Math.max(0, ...((before.g5 && before.g5.films) || []).map(f => f.n));
  killServer(); log('server killed during', before.task && before.task.what);
  await page.waitForTimeout(3000);
  server('restart');
  v = await view();
  const resumed = v.runner_alive && v.task && v.task.stage === 'film';
  ok('S8', 'after the restart the interrupted render is recorded as interrupted and the film is started again by itself',
     resumed && (await (await ctx.request.get(`${BASE}/api/copilot/${PID}`)).json()).history.some(h => /interrupted|assemble/.test(h.summary)), { task: v.task, interrupted: v.interrupted });
  ok('S8', 'the cut-off render is listed as interrupted (a film job, not just any history line)', (v.interrupted || []).some(j => /assemble|film/.test(j.what)), v.interrupted);
  v = await waitView(v => v.g5 && v.waiting.includes('G5') && v.g5.films.some(f => f.state === 'ok' && f.n > cutN), 'film after restart', 60);
  const dup = v.scenes.flatMap(s => s.versions.map(x => x.inputs).filter((h, i, a) => a.indexOf(h) !== i).map(h => s.id + ':' + h));
  ok('S8', 'a NEW film completed after the interruption, nothing generated twice', v.waiting.includes('G5') && dup.length === 0
     && v.g5.films.some(f => f.state === 'ok' && f.n > cutN), { cutN, films: v.g5.films, dup });
  ok('S8', 'no film is left "running" after the restart', !v.g5.films.some(f => f.state === 'running'), v.g5.films);
  ok('S4', 'after the style change every scene was redrawn in the new style', diff(f3, filmScenes(v)).length === 13, diff(f3, filmScenes(v)));
  const f4 = filmScenes(v);
  // ============================================================ S9 (part 2): approve this film first, so the hook change below can outdate a REAL approval
  v = await approveG5('S9');
  ok('S9', 'Gate 5 approved before the hook change', v.validity.G5.valid && v.validity.G2.valid, { G2: v.validity.G2, G5: v.validity.G5 });
  // ============================================================ S3 hook changed after narration
  const takesBefore = Object.fromEntries((await view()).g3.lines.map(l => [l.line, l.take]));
  await go('g2');
  await openAll(); await page.locator('[data-hook="H3"]').click(); await page.waitForTimeout(1500);
  v = await view();
  ok('S9', 'changing the hook outdates the script approval and the APPROVED film (and keeps the style approval)',
     !v.validity.G2.valid && !v.validity.G5.valid && v.validity.G4.valid && (v.gates.G5 || []).some(r => r.decision === 'approved'), { G2: v.validity.G2, G4: v.validity.G4, G5: v.validity.G5 });
  v = await waitView(v => v.waiting.includes('G2'), 'G2 for the new hook', 10);
  await go('g2');
  for (const c of await page.locator('[data-ack]').all()) await c.check();
  await gateBtn('G2', 'approved').click(); await page.waitForTimeout(1500);
  v = await waitView(v => v.waiting.includes('G3') && v.g3.mix_current, 'G3 after the hook', 15);
  const changedTakes = v.g3.lines.filter(l => l.take !== takesBefore[l.line]).map(l => l.line);
  ok('S3', 'only the hook line was voiced again; the other approved takes are untouched', JSON.stringify(changedTakes) === '["h"]', changedTakes);
  const hookPlay = async v => { const seg = v.g3.mix.segments.find(s => s.line === 'h'); await playRange('#mix', seg.start, seg.end + 0.1, 1); };
  await idleVoice(); await go('g3');
  await hookPlay(await view());
  if (await page.locator('#ackqa').count()) await page.check('#ackqa');
  await gateBtn('G3', 'approved').click(); await page.waitForTimeout(1500);
  v = await approveG3(hookPlay, 'S3');
  ok('S3', 'Gate 3 needed only the changed line', v.validity.G3.valid, v.validity.G3);
  // H3 opens on a drawing that draws itself in: its first frame is an empty page, which the Co-Pilot cannot fix by itself
  v = await waitView(v => (v.g5 && v.waiting.includes('G5') && diff(f4, filmScenes(v)).length > 0) || v.exceptions.some(x => x.scene === 'h' && x.status === 'open'), 'film or opening-scene question', 45);
  const exh = v.exceptions.find(x => x.scene === 'h' && x.status === 'open');
  if (exh) {
    ok('Reg', 'a blank opening the Co-Pilot cannot fix (a drawing hook) is caught and brought to you', /empty page/.test(exh.detail), exh.detail);
    await go('ex/' + exh.id); await shot('14-blank-opening');
    await page.fill('#exnote', 'مقبول في المسودة: سأقرر لاحقًا بين H1 وH3'); await page.locator('[data-exd="accept_best"]').click(); await page.waitForTimeout(1500);
    v = await waitView(v => v.g5 && v.waiting.includes('G5') && diff(f4, filmScenes(v)).length > 0, 'film with the new hook', 60);
  }
  ok('S3', 'only the opening scene was redone for the new hook', JSON.stringify(diff(f4, filmScenes(v))) === '["h"]', diff(f4, filmScenes(v)));
  ok('Reg', 'the new hook is the one rendered', !v.g5.findings.some(f => f.code === 'HOOK_MISMATCH'));
  // ============================================================ S12 draft played and reviewed on the phone, Gate 5
  await go('g5'); await shot('11-g5-final');
  ok('S12', 'no sideways scrolling on the film screen', (await overflow()) === 0);
  v = await view();
  const l5s = v.g5.timeline.find(s => s.id === 'l5');
  await playRange('#film', l5s.start + 0.3, l5s.start + 1.3, 1);
  ok('S12', 'the scene timeline follows the film', (await page.locator('#ftl button.on').getAttribute('data-sid').catch(() => null)) === 'l5');
  v = await approveG5('S12');
  ok('S1', 'Gate 5: you approved the complete draft', v.validity.G5.valid, v.validity.G5);
  // ============================================================ S11 paid calls
  v = await waitView(v => v.g6 && v.g6.plan, 'paid plan', 10);
  await go('g6'); await shot('12-g6');
  await page.fill('#g6c', String(v.g6.plan.chars_total)); await page.locator('[data-g6]').click(); await page.waitForTimeout(800);
  const t6 = await toastText(); await closeToast();
  ok('S11', 'paid narration cannot be authorized here (blockers listed)', /not authorized|disabled|مُفوَّض|معطّلة/.test(t6), t6);
  const fg = await ctx.request.post(`${BASE}/api/copilot`, { data: { project: PID, action: 'final_generate', args: {} } });
  ok('S11', 'the page has no route to paid generation', fg.status() === 422);
  const g6o = await ctx.request.post(`${BASE}/api/copilot`, { data: { project: PID, action: 'cp_gate', args: { gate: 'G6', decision: 'approved', content_hash: 'old', confirm_text: '1' } } });
  ok('S11', 'an outdated paid approval is rejected', g6o.status() === 422, (await g6o.json()).reason);
  await ctx.request.post(`${BASE}/api/copilot`, { data: { project: PID, action: 'cp_settings', args: { worker: 'claude-code' } } });
  v = await view();
  ok('S11', 'the real AI worker has a $0 budget until you authorize one', v.ai.budget_usd === 0, v.ai);
  // a real attempt through the server's own AI call (not a reading of the screen): it must be refused before anything runs
  const ledger = () => { try { return fs.readFileSync(`${VAR}/copilot-ai-usage.jsonl`, 'utf8').split('\n').filter(Boolean).map(JSON.parse); } catch { return []; } };
  const n0 = ledger().length, calls0 = v.ai.n_calls;
  const pr = await (await ctx.request.post(`${BASE}/api/copilot/_test`, { data: { ai_probe: { project: PID, kind: 'fact_check' } } })).json();
  v = await view();
  ok('S11', 'an AI call with the real worker selected is refused by the server, nothing is run or spent',
     !!pr.refused && ledger().length === n0 && v.ai.n_calls === calls0 && !ledger().some(x => x.worker === 'claude-code') && v.ai.spent_usd === 0,
     { refused: pr.refused, ledger: ledger().length - n0, spent: v.ai.spent_usd });
  await ctx.request.post(`${BASE}/api/copilot`, { data: { project: PID, action: 'cp_settings', args: { worker: 'mock' } } });
  // ============================================================ S10 switch to Manual
  await go('');
  await openAll(); await page.locator('[data-manual]').click(); await page.waitForTimeout(400);
  ok('S10', 'switching to Manual asks first (nothing happens on the first tap)', (await view()).mode === 'copilot' && await page.locator('[data-ask-ok]').isVisible());
  await page.locator('[data-ask-ok]').click(); await page.waitForTimeout(1500);
  v = await view();
  ok('S10', 'switch to Manual: the Co-Pilot stops, every approval is kept', v.mode === 'manual' && v.run === 'stopped' && v.validity.G5.valid && v.validity.G3.valid, { mode: v.mode, run: v.run });
  await page.goto(`${BASE}/studio/classic#/p/${PID}/`); await page.waitForTimeout(2000); await shot('13-classic');
  ok('S10', 'the classic Studio opens the same project (its own page, not the list)', ((await page.locator('#ptitle').textContent().catch(() => '')) || '').includes('Rolex Oyster'));
  // ... and back: the page shows what you did by hand, what still waits for you and what it could cost, before anything changes
  await page.goto(`${BASE}/studio#/p/${PID}`); await page.waitForTimeout(1200);
  await page.locator('[data-back]').first().click(); await page.waitForTimeout(500);
  const sheet = (await page.locator('.ask').textContent().catch(() => '')) || '';
  ok('S10', 'going back to the Co-Pilot shows a summary and the cost first; nothing happens on the first tap',
     (await view()).mode === 'manual' && /(ينتظر موافقتك|Waiting for your approval)/.test(sheet) && /(صرف|تكلفة|spend|cost)/i.test(sheet), sheet.slice(0, 240));
  await shot('13b-back');
  await page.locator('[data-ask-ok]').click(); await page.waitForTimeout(1500);
  v = await view();
  ok('S10', 'back to the Co-Pilot: every approval kept, nothing paid started, no AI spent',
     v.mode === 'copilot' && v.validity.G5.valid && v.validity.G3.valid && v.ai.spent_usd === 0 && !(v.g6 && v.g6.authorized), { mode: v.mode, run: v.run, spent: v.ai.spent_usd });
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
fs.writeFileSync(`${OUT}/results.json`, JSON.stringify({ pid: PID, results: R, errors }, null, 1));
log('done', R.filter(r => r.result === 'PASS').length, 'pass', R.filter(r => r.result === 'FAIL').length, 'fail');
await b.close();
