// M6 interface + playback test against the LOCAL server (run it on a copy of the event log).
//   node tools/ui_m6_test.mjs http://127.0.0.1:8766 var/shots/m6
// Phone = 390×844 (iPhone 12–15 size) with touch; desktop = 1366×900. Chromium only: WebKit (Safari) is not
// installed here, so real-iPhone playback is NOT proven by this test (see the report).
import { createRequire } from 'node:module';
import fs from 'node:fs';
const require = createRequire(import.meta.url);
const { chromium, devices } = require(process.env.PW_MODULE || '/opt/node22/lib/node_modules/playwright');
const [base, out] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
const res = [], voice = []; const ok = (n, c, d = '') => res.push({ name: n, pass: !!c, detail: String(d) }); const errors = [];
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args: ['--no-proxy-server', '--autoplay-policy=no-user-gesture-required'] });
const iphone = { ...devices['iPhone 13'] }; delete iphone.defaultBrowserType;
async function open(kind, scheme, hash) {
  const ctx = await b.newContext(kind === 'phone' ? { ...iphone, colorScheme: scheme } : { viewport: { width: 1366, height: 900 }, deviceScaleFactor: 2, colorScheme: scheme });
  await ctx.route((u) => !u.href.startsWith(base) && !u.href.startsWith('https://fonts.'), (r) => r.abort());
  await ctx.route(/fonts\.(googleapis|gstatic)/, (r) => r.abort());
  const p = await ctx.newPage(); p.on('pageerror', (e) => errors.push(e.message));
  await p.goto(base + '/#' + hash); await p.waitForTimeout(600); return p;
}
const noScroll = (p) => p.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1);
const shot = (p, n, full = false) => p.screenshot({ path: `${out}/${n}.png`, fullPage: full });
const snap = await (await fetch(base + '/api/snapshot')).json();

// ---------------- WATCH (phone)
let p = await open('phone', 'dark', 'dh~watch');
ok('watch: player is the first thing on screen', await p.evaluate(() => { const v = document.querySelector('#pv'); const r = v.getBoundingClientRect(); return r.top < 200 && r.height > 300; }));
ok('watch: next action shown', (await p.locator('.next').textContent()).includes('Next action'));
ok('watch: details folded away', (await p.locator('details.fold').count()) >= 4 && (await p.locator('details.fold[open]').count()) === 0);
ok('watch: no percentage', !/\d+(\.\d+)?\s?%/.test(await p.locator('main').textContent()));
const pv = await p.evaluate(async () => { const v = document.querySelector('#pv'); v.muted = true; await v.play().catch(e => e.message);
  await new Promise((r) => setTimeout(r, 1500)); return { src: v.currentSrc.split('/').pop(), t: v.currentTime, dur: v.duration, err: v.error && v.error.code }; });
ok('watch: episode preview really plays (time advances)', pv.t > 0.5 && !pv.err, JSON.stringify(pv));
await p.evaluate(() => { const v = document.querySelector('#pv'); v.pause(); v.currentTime = 0; });
await shot(p, 'phone-dark-watch-dh');
ok('phone: no sideways scroll (watch)', await noScroll(p));

// ---------------- TIMELINE (phone)
await p.goto(base + '/#dh~timeline'); await p.waitForTimeout(500);
ok('timeline: 20 thumbnails in the strip', (await p.locator('.strip button img').count()) === 20);
await p.locator('.strip button[data-seekscene="b4"]').click(); await p.waitForTimeout(1500);
const tl = await p.evaluate(() => { const v = document.querySelector('#tlv'); return { t: v.currentTime, paused: v.paused }; });
const b4 = snap.projects['diabetes-history'].videos[0].scenes.find((s) => s.id === 'b4');
ok('timeline: tapping a scene jumps the video to that moment', tl.t >= b4.start && tl.t < b4.end + 1, JSON.stringify(tl) + ' b4 ' + b4.start);
ok('timeline: current scene highlighted', (await p.locator('.srow.now').getAttribute('id')) === 'row-b4');
await p.evaluate(() => document.querySelector('#tlv').pause());
ok('phone: no sideways scroll (timeline)', await noScroll(p));
await shot(p, 'phone-dark-timeline-dh');

// ---------------- ART (phone)
await p.goto(base + '/#dh~art~b1'); await p.waitForTimeout(400);
ok('art: concepts are labelled proposals', (await p.locator('.card .pill', { hasText: 'Proposal' }).count()) >= 2);
ok('art: references are labelled as not drawn for the scene', (await p.locator('.pv .lab').first().textContent()).includes('Not drawn for b1'));
await shot(p, 'phone-dark-art-concepts');
await p.locator('button[data-arttab="revisions"]').click(); await p.waitForTimeout(300);
ok('art: three real revisions of b1', (await p.locator('.card img').count()) === 3);
await shot(p, 'phone-dark-art-revisions');
await p.goto(base + '/#dh~reviews'); await p.waitForTimeout(400);
{ const scenes = snap.projects['diabetes-history'].videos[0].scenes.map((x) => x.id);
  const art = snap.review_tasks.filter((t) => t.type === 'art' && t.video === 'ep7');
  const perScene = scenes.map((id) => art.filter((t) => t.scene === id).length);
  const ids = art.flatMap((t) => t.findings.map((f) => f.id));
  ok('reviews: exactly one art task per scene (20 scenes, 20 tasks)', scenes.length === 20 && perScene.every((n) => n === 1) && art.length === 20);
  ok('reviews: no finding counted twice', new Set(ids).size === ids.length);
  ok('reviews: every art task card is on the page once', (await p.locator('article.task[id^="task-art-ep7-"]').count()) === art.filter((t) => t.status !== 'done').length); }
ok('phone: no sideways scroll (reviews)', await noScroll(p));
await shot(p, 'phone-dark-reviews');
await p.context().close();

// ---------------- VOICE PLAYBACK: all flagged lines on the phone
p = await open('phone', 'light', 'tk~reviews');
const checks = snap.inbox_checks;
for (const c of checks) {
  const card = p.locator(`.check[data-check="${c.id}"]`);
  await card.scrollIntoViewIfNeeded();
  const before = await card.locator('button[data-dec="article_heard"]').isDisabled();
  await card.locator('button[data-word]').click();
  await p.waitForFunction((id) => { const a = document.querySelector(`audio[data-audio="${id}"]`); return a && a.played.length && a.paused; }, c.id, { timeout: 15000 }).catch(() => {});
  await p.waitForTimeout(200);
  const r = await p.evaluate((id) => { const a = document.querySelector(`audio[data-audio="${id}"]`); const rs = []; for (let i = 0; i < a.played.length; i++) rs.push([+a.played.start(i).toFixed(2), +a.played.end(i).toFixed(2)]);
    return { duration: +a.duration.toFixed(3), played: rs, gate: a.closest('.check').querySelector('.gate').textContent, error: a.error && a.error.code }; }, c.id);
  const after = await card.locator('button[data-dec="article_heard"]').isDisabled();
  voice.push({ check: c.id, line: c.line, word: c.written, file: c.audio_file, expected_duration: c.duration, browser_duration: r.duration,
               word: [c.word_s, c.word_e], played: r.played, answer_blocked_before_playing: before, answer_enabled_after: !after, gate: r.gate, error: r.error });
}
const lines = [...new Set(checks.map((c) => c.line))];
ok(`voice: all ${checks.length} checks (${lines.length} lines) loaded with the right duration`, voice.every((v) => Math.abs(v.browser_duration - v.expected_duration) <= 0.25), voice.map((v) => v.browser_duration).join(','));
ok('voice: answers are blocked until the word has played', voice.every((v) => v.answer_blocked_before_playing));
ok('voice: the flagged word actually played for every check', voice.every((v) => v.answer_enabled_after && v.gate.includes('✓')), voice.filter((v) => !v.answer_enabled_after).map((v) => v.check).join(','));
await shot(p, 'phone-light-voice-checks');
// one answer recorded through the local app, with its playback proof
const first = checks[0];
await p.locator(`.check[data-check="${first.id}"] button[data-dec="unsure"]`).click(); await p.waitForTimeout(700);
const afterSnap = await (await fetch(base + '/api/snapshot')).json();
const rec = afterSnap.inbox_checks.find((c) => c.id === first.id).decision;
ok('voice: answer recorded in the event log with playback proof', rec && rec.decision === 'unsure' && rec.event > 0, JSON.stringify(rec));
ok('voice: the answered line moves to Done', afterSnap.review_tasks.find((t) => t.id === 'task-voice-' + first.line).status === 'done');
// the server refuses a listening answer with no proof, or with proof from the wrong file
const post = (body) => p.evaluate(async ([u, bd]) => { const r = await fetch(u + '/api/decision', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(bd) }); return [r.status, (await r.json()).reason]; }, [base, body]);
const c2 = checks[1];
const noProof = await post({ item: c2.id, decision: 'article_heard' });
ok('server refuses a listening answer without playback proof (422)', noProof[0] === 422, noProof.join(' '));
const wrongFile = await post({ item: c2.id, decision: 'article_heard', playback: { src: '/media/royal-oak/audio/p1-0.mp3', duration: c2.duration, played: [[0, 30]] } });
ok('server refuses proof from another audio file', wrongFile[0] === 422, wrongFile.join(' '));
const notHeard = await post({ item: c2.id, decision: 'article_heard', playback: { src: '/media/royal-oak/audio/' + c2.audio_file, duration: c2.duration, played: [[0, 0.5]] } });
ok('server refuses when the flagged word was not played', notHeard[0] === 422, notHeard.join(' '));
// a broken audio file can never produce a listening result
await p.evaluate(() => { const a = document.querySelectorAll('audio[data-audio]')[2]; a.src = '/media/royal-oak/audio/missing.mp3'; a.load(); });
await p.waitForTimeout(800);
ok('broken audio: shown as a failure, answers stay blocked', await p.evaluate(() => { const c = document.querySelectorAll('.check')[2]; return c.textContent.includes('did not play') && c.querySelector('button[data-dec="article_heard"]').disabled; }));
await p.context().close();

// ---------------- concept selection is not approval; approval locks a version
p = await open('desktop', 'light', 'dh~art~b3');
await p.locator('.card').first().locator('button[data-dec="concept_selected"]').click(); await p.waitForTimeout(700);
const s3 = await (await fetch(base + '/api/snapshot')).json();
const b3 = s3.projects['diabetes-history'].videos[0].scenes.find((s) => s.id === 'b3');
ok('concept selected is recorded as a selection, not an approval', b3.concepts.options[0].decision.decision === 'concept_selected' && b3.versions[0].decision === null);
await p.locator('input[data-cmp]').nth(0).check(); await p.locator('input[data-cmp]').nth(1).check(); await p.locator('#cmpBtn').click(); await p.waitForTimeout(300);
ok('concepts: side-by-side comparison opens', (await p.locator('#lb .compare figure').count()) === 2);
{ const caps = await p.locator('#lb .compare figcaption').allTextContents(); ok('concepts: compared references keep their "not drawn for this scene" label', caps.every((c) => /Proposal/.test(c)) && caps.some((c) => /Not drawn for b3/.test(c)), caps.join(' | ')); }
await shot(p, 'desktop-light-art-compare'); await p.locator('#lbClose').click();
await shot(p, 'desktop-light-art-b3', false);
await p.goto(base + '/#dh~art~b1'); await p.waitForTimeout(300); await p.locator('button[data-arttab="revisions"]').click(); await p.waitForTimeout(200);
await p.locator('.card').nth(2).locator('button[data-dec="approved"]').click(); await p.waitForTimeout(700);
ok('approved version is locked', await p.locator('.card').nth(2).locator('button[data-dec="rejected"]').isDisabled());
await shot(p, 'desktop-light-art-revisions');
for (const [h, n] of [['dh~watch', 'desktop-dark-watch-dh'], ['tk~watch', 'desktop-dark-watch-tk'], ['dh~timeline', 'desktop-dark-timeline'], ['dh~reviews', 'desktop-dark-reviews'], ['dh~identity', 'desktop-dark-identity'], ['tk~costs', 'desktop-dark-costs']]) {
  const q = await open('desktop', 'dark', h); await shot(q, n); if (h === 'dh~identity') await shot(q, n + '-full', true); await q.context().close();
}
for (const [h, n] of [['tk~watch', 'phone-light-watch-tk'], ['tk~timeline', 'phone-light-timeline-tk'], ['tk~identity', 'phone-light-identity-tk'], ['dh~identity', 'phone-light-identity-dh']]) {
  const q = await open('phone', 'light', h); ok('phone: no sideways scroll ' + h, await noScroll(q)); await shot(q, n); await q.context().close();
}
await p.context().close(); await b.close();
ok('no page errors', errors.length === 0, errors.join(' | '));
fs.writeFileSync(`${out}/results.json`, JSON.stringify(res, null, 1));
fs.writeFileSync(`${out}/voice-playback.json`, JSON.stringify(voice, null, 1));
for (const r of res) console.log((r.pass ? 'PASS ' : 'FAIL ') + r.name + (r.pass ? '' : '  (' + r.detail + ')'));
const f = res.filter((r) => !r.pass).length; console.log(`${res.length - f}/${res.length} passed`); process.exit(f ? 1 : 0);
