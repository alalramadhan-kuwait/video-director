// Guided review flow + playback test against the LOCAL server (run it on a copy of the event log).
//   node tools/ui_flow_test.mjs http://127.0.0.1:8766 var/shots/m6b [OLD_BASE]
// Phone = iPhone 13 (390×844, touch); desktop = 1366×900. Chromium only: WebKit (Safari) is not installed here, so
// real-iPhone playback is NOT proven by this test. OLD_BASE (optional) serves the previous page for the word counts.
import { createRequire } from 'node:module';
import fs from 'node:fs';
const require = createRequire(import.meta.url);
const { chromium, devices } = require(process.env.PW_MODULE || '/opt/node22/lib/node_modules/playwright');
const [base, out, oldBase] = process.argv.slice(2);
fs.mkdirSync(out, { recursive: true });
const res = [], voice = [], words = {}; const ok = (n, c, d = '') => res.push({ name: n, pass: !!c, detail: String(d) }); const errors = [];
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args: ['--no-proxy-server', '--autoplay-policy=no-user-gesture-required'] });
const iphone = { ...devices['iPhone 13'] }; delete iphone.defaultBrowserType;
async function open(kind, scheme, hash, at = base) {
  const ctx = await b.newContext(kind === 'phone' ? { ...iphone, colorScheme: scheme } : { viewport: { width: 1366, height: 900 }, deviceScaleFactor: 2, colorScheme: scheme });
  await ctx.route((u) => !u.href.startsWith(at) && !u.href.startsWith('https://fonts.'), (r) => r.abort());
  await ctx.route(/fonts\.(googleapis|gstatic)/, (r) => r.abort());
  const p = await ctx.newPage(); p.on('pageerror', (e) => errors.push(e.message));
  await p.goto(at + '/#' + hash); await p.waitForTimeout(600); return p;
}
const go = async (p, hash) => { await p.goto(base + '/#' + hash); await p.waitForTimeout(450); };
const noScroll = (p) => p.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1);
const shot = (p, n, full = false) => p.screenshot({ path: `${out}/${n}.png`, fullPage: full });
const wc = (p) => p.evaluate(() => document.querySelector('main').innerText.split(/\s+/).filter(Boolean).length);
const api = async () => (await fetch(base + '/api/snapshot')).json();
const dec = (s, item) => { const t = s.review_tasks.find((x) => x.id === item); if (t) return t.decision;
  for (const sc of s.projects['diabetes-history'].videos[0].scenes) { const f = sc.findings.find((x) => x.id === item); if (f) return f.decision; } return null; };
const inView = (p, sel) => p.evaluate((s) => { const r = document.querySelector(s).getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight + 1; }, sel);
let snap = await api();
const scenes = snap.projects['diabetes-history'].videos[0].scenes;

// ---------------- HOME: the film, four steps, one next button
let p = await open('phone', 'dark', 'dh~review');
ok('home: the film is the first thing on screen', await p.evaluate(() => { const r = document.querySelector('#pv').getBoundingClientRect(); return r.top < 140 && r.height > 250; }));
ok('home: four steps (Voice, Scenes, Final video, Publish)', (await p.locator('ol.path li').allTextContents()).map((t) => t.replace(/\s+/g, ' ')).every((t, i) => t.includes(['Voice', 'Scenes', 'Final video', 'Publish'][i])) && (await p.locator('ol.path li').count()) === 4);
ok('home: one next button points at the first scene', (await p.locator('#nextBtn').textContent()).includes('Review scene ' + scenes[0].id));
ok('home: voice done, scenes current, final waits, publish blocked', JSON.stringify(await p.locator('ol.path li').evaluateAll((ls) => ls.map((l) => l.className))) === JSON.stringify(['done', 'now', 'wait', 'blocked']));
ok('home: next button visible without scrolling on a phone', await inView(p, '#nextBtn'));
words['Review (home)'] = await wc(p);
ok('phone: no sideways scroll (home)', await noScroll(p));
await shot(p, 'phone-dark-home-dh');
await p.locator('#nextBtn').click(); await p.waitForTimeout(500);
ok('home: next button opens the scene review', (await p.evaluate(() => location.hash)) === '#dh~scene~' + scenes[0].id);

// ---------------- SCENE REVIEW: one scene at a time, actions in a bar
const s0 = scenes[0], s1 = scenes[1];
ok('scene: the action bar is on screen without scrolling', await inView(p, '.actionbar'));
ok('scene: tabs are hidden while reviewing (phone)', await p.locator('nav.tabs').isHidden());
ok('scene: one dot per scene', (await p.locator('.dots a').count()) === scenes.length);
ok('scene: every reviewer note of the scene is here', (await p.locator('.issue').count()) === s0.findings.length, `${await p.locator('.issue').count()} vs ${s0.findings.length}`);
const sv = await p.evaluate(async () => { const v = document.querySelector('#sv'); await new Promise((r) => setTimeout(r, 1200)); return { t: v.currentTime, err: v.error && v.error.code }; });
ok('scene: the scene clip plays', sv.t > 0.3 && !sv.err, JSON.stringify(sv));
words['Scene review'] = await wc(p);
ok('phone: no sideways scroll (scene)', await noScroll(p));
await shot(p, 'phone-dark-scene-a1');
await p.locator('#okBtn').click(); await p.waitForTimeout(900);
snap = await api();
ok('scene: “Approve” records the scene as approved', (dec(snap, 'art-ep7-' + s0.id) || {}).decision === 'approved');
ok('scene: moves on to the next scene to review', (await p.evaluate(() => location.hash)) === '#dh~scene~' + s1.id);
ok('scene: the approved scene shows green in the dots', await p.locator('.dots a').first().evaluate((a) => a.classList.contains('ok')));
// a2: open a note, change what to fix, send the fixes
await p.locator('.issue button.itxt').first().click(); await p.waitForTimeout(250);
ok('scene: tapping a note shows all of it and the suggestion', (await p.locator('.issue.open .txt').textContent()).trim() === s1.findings.find((f) => f.id === (s1.findings[0].id)).problem.trim() || (await p.locator('.issue.open').count()) === 1);
await shot(p, 'phone-dark-scene-a2-open');
const before = await p.locator('button.fixbtn[aria-pressed="true"]').count();
await p.locator('button.fixbtn').first().click(); await p.waitForTimeout(250);
const marked = await p.locator('button.fixbtn[aria-pressed="true"]').evaluateAll((bs) => bs.map((x) => x.dataset.fix));
ok('scene: the Fix button counts the marked notes', (await p.locator('#fixBtn').textContent()).includes(String(marked.length)) && marked.length !== before);
if (!marked.length) { await p.locator('button.fixbtn').first().click(); await p.waitForTimeout(200); marked.push(await p.locator('button.fixbtn').first().getAttribute('data-fix')); }
await p.locator('#fixBtn').click(); await p.waitForTimeout(1200);
snap = await api();
const t1 = dec(snap, 'art-ep7-' + s1.id);
ok('scene: “Fix” records fixes requested for the scene, listing the notes', t1 && t1.decision === 'changes_requested' && marked.every((f) => t1.note.includes(f)), JSON.stringify(t1));
ok('scene: each marked note is recorded as a fix', marked.every((f) => (dec(snap, f) || {}).decision === 'accepted'));
ok('scene: moves on after asking for fixes', (await p.evaluate(() => location.hash)) === '#dh~scene~' + scenes[2].id);
await go(p, 'dh~scene~' + s0.id);
ok('scene: an approved scene is locked (only “Reopen for fixes”)', (await p.locator('#okBtn').count()) === 0 && (await p.locator('button[data-scenefix]').count()) === 1);
await go(p, 'dh~review');
ok('home: progress counts reviewed scenes', (await p.locator('li[data-step="scenes"] .cnt').textContent()).trim() === `2/${scenes.length}`);
ok('home: next button moves to the next scene', (await p.locator('#nextBtn').textContent()).includes('Review scene ' + scenes[2].id));
await go(p, 'dh~final');
ok('final: waits until every scene is reviewed (no approve button)', (await p.locator('.actionbar').count()) === 0 && (await p.locator('main').textContent()).includes(`${scenes.length - 2} scenes still to review`));
await shot(p, 'phone-dark-final-waiting');

// ---------------- SCENES: film + list, tap a picture to jump there
await go(p, 'dh~scenes');
ok('scenes: one row per scene', (await p.locator('.srow').count()) === scenes.length);
const b4 = scenes.find((s) => s.id === 'b4');
await p.locator('.srow .thumb[data-seekscene="b4"]').click(); await p.waitForTimeout(1500);
const tl = await p.evaluate(() => { const v = document.querySelector('#tlv'); return { t: v.currentTime }; });
ok('scenes: tapping a picture jumps the film to that moment', tl.t >= b4.start && tl.t < b4.end + 1, JSON.stringify(tl));
ok('scenes: the playing scene is highlighted', (await p.locator('.srow.now').getAttribute('id')) === 'row-b4');
await p.evaluate(() => document.querySelector('#tlv').pause());
words['Scenes'] = await wc(p);
ok('phone: no sideways scroll (scenes)', await noScroll(p));
await shot(p, 'phone-dark-scenes');

// ---------------- ALL TASKS: grouped, one task per scene
await go(p, 'dh~tasks');
snap = await api();
{ const art = snap.review_tasks.filter((t) => t.type === 'art' && t.video === 'ep7');
  const ids = art.flatMap((t) => t.findings.map((f) => f.id));
  ok('tasks: exactly one art task per scene', scenes.every((s) => art.filter((t) => t.scene === s.id).length === 1) && art.length === scenes.length);
  ok('tasks: no note counted twice', new Set(ids).size === ids.length);
  ok('tasks: four groups plus done and all', (await p.locator('.summary button').count()) === 6);
  ok('tasks: every open art task listed once', (await p.locator('article.task[id^="task-art-ep7-"]').count()) === art.filter((t) => t.status !== 'done').length); }
words['All tasks'] = await wc(p);
ok('phone: no sideways scroll (tasks)', await noScroll(p));
await shot(p, 'phone-dark-tasks');
await p.context().close();

// ---------------- VOICE: one check at a time, answers need the word to play
p = await open('phone', 'light', 'tk~review');
ok('home (Time Keeper): next button starts the listening checks', (await p.locator('#nextBtn').textContent()).includes('Listen: check 1 of ' + snap.inbox_checks.length));
await shot(p, 'phone-light-home-tk');
const checks = snap.inbox_checks;
for (let i = 0; i < checks.length; i++) {
  const c = checks[i];
  await go(p, 'tk~voice~' + i);
  const blocked = await p.locator('button[data-ans="article_heard"]').isDisabled();
  await p.locator('button[data-word]').click();
  await p.waitForFunction((id) => { const a = document.querySelector(`audio[data-audio="${id}"]`); return a && a.played.length && a.paused; }, c.id, { timeout: 15000 }).catch(() => {});
  await p.waitForTimeout(200);
  const r = await p.evaluate((id) => { const a = document.querySelector(`audio[data-audio="${id}"]`); const rs = []; for (let k = 0; k < a.played.length; k++) rs.push([+a.played.start(k).toFixed(2), +a.played.end(k).toFixed(2)]);
    return { duration: +a.duration.toFixed(3), played: rs, gate: document.querySelector('.gate').textContent, error: a.error && a.error.code }; }, c.id);
  const enabled = !(await p.locator('button[data-ans="article_heard"]').isDisabled());
  voice.push({ check: c.id, line: c.line, word: c.written, file: c.audio_file, expected_duration: c.duration, browser_duration: r.duration,
               word_at: [c.word_s, c.word_e], played: r.played, answer_blocked_before_playing: blocked, answer_enabled_after: enabled, gate: r.gate, error: r.error });
  if (i === 0) { words['Listening check'] = await wc(p); ok('voice: the answer bar is on screen without scrolling', await inView(p, '.actionbar')); ok('phone: no sideways scroll (voice)', await noScroll(p)); await shot(p, 'phone-light-voice'); }
}
const lines = [...new Set(checks.map((c) => c.line))];
ok(`voice: all ${checks.length} checks (${lines.length} lines) loaded with the right duration`, voice.every((v) => Math.abs(v.browser_duration - v.expected_duration) <= 0.25), voice.map((v) => v.browser_duration).join(','));
ok('voice: answers are blocked until the word has played', voice.every((v) => v.answer_blocked_before_playing));
ok('voice: the flagged word actually played for every check', voice.every((v) => v.answer_enabled_after && v.gate.includes('✓')), voice.filter((v) => !v.answer_enabled_after).map((v) => v.check).join(','));
// answer the first check through the bar
await go(p, 'tk~voice~0');
await p.locator('button[data-word]').click();
await p.waitForFunction((id) => { const a = document.querySelector(`audio[data-audio="${id}"]`); return a && a.played.length && a.paused; }, checks[0].id, { timeout: 15000 });
await p.waitForTimeout(200);
await p.locator('button[data-ans="unsure"]').click(); await p.waitForTimeout(900);
snap = await api();
const rec = snap.inbox_checks[0].decision;
ok('voice: the answer is recorded with its playback proof', rec && rec.decision === 'unsure' && rec.event > 0, JSON.stringify(rec));
ok('voice: moves on to the next check', (await p.evaluate(() => location.hash)) === '#tk~voice~1');
await go(p, 'tk~review');
ok('home (Time Keeper): voice progress counts the answer', (await p.locator('li[data-step="voice"] .cnt').textContent()).trim() === `1/${checks.length}`);
// the server refuses a listening answer with no proof, proof from another file, or a word that was not played
const post = (body) => p.evaluate(async ([u, bd]) => { const r = await fetch(u + '/api/decision', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(bd) }); return [r.status, (await r.json()).reason]; }, [base, body]);
const c2 = checks[1];
const noProof = await post({ item: c2.id, decision: 'article_heard' });
ok('server refuses a listening answer without playback proof (422)', noProof[0] === 422, noProof.join(' '));
const wrongFile = await post({ item: c2.id, decision: 'article_heard', playback: { src: '/media/royal-oak/audio/p1-0.mp3', duration: c2.duration, played: [[0, 30]] } });
ok('server refuses proof from another audio file', wrongFile[0] === 422, wrongFile.join(' '));
const notHeard = await post({ item: c2.id, decision: 'article_heard', playback: { src: '/media/royal-oak/audio/' + c2.audio_file, duration: c2.duration, played: [[0, 0.5]] } });
ok('server refuses when the flagged word was not played', notHeard[0] === 422, notHeard.join(' '));
// a broken audio file can never produce a listening result
await go(p, 'tk~voice~2');
await p.evaluate(() => { const a = document.querySelector('audio[data-audio]'); a.src = '/media/royal-oak/audio/missing.mp3'; a.load(); });
await p.waitForTimeout(900);
ok('broken audio: shown as a failure, answers stay blocked, failure can be reported', await p.evaluate(() => document.querySelector('.gate').textContent.includes('would not play')
  && document.querySelector('button[data-ans="article_heard"]').disabled && !!document.querySelector('button[data-dec="playback_failed"]')));
await p.context().close();

// ---------------- ART: concepts are proposals; choosing one is not approving; approving a version locks it
p = await open('desktop', 'light', 'dh~art~b3');
await p.locator('.card').first().locator('button[data-dec="concept_selected"]').click(); await p.waitForTimeout(700);
snap = await api();
const b3 = snap.projects['diabetes-history'].videos[0].scenes.find((s) => s.id === 'b3');
ok('art: choosing a look is recorded as a selection, not an approval', b3.concepts.options[0].decision.decision === 'concept_selected' && b3.versions[0].decision === null);
ok('art: every look is labelled a proposal', (await p.locator('.card:not([data-look]) .pill', { hasText: 'Proposal' }).count()) === b3.concepts.options.length);
await p.locator('input[data-cmp]').nth(0).check(); await p.locator('input[data-cmp]').nth(1).check(); await p.locator('#cmpBtn').click(); await p.waitForTimeout(300);
{ const caps = await p.locator('#lb .compare figcaption').allTextContents();
  ok('art: compare shows them side by side, references keep “not drawn for this scene”', caps.length === 2 && caps.every((c) => /Proposal/.test(c)) && caps.some((c) => /Not drawn for b3/.test(c)), caps.join(' | ')); }
await shot(p, 'desktop-light-art-compare'); await p.locator('#lbClose').click();
await shot(p, 'desktop-light-art-b3');
await p.goto(base + '/#dh~art~b1'); await p.waitForTimeout(300); await p.locator('button[data-arttab="revisions"]').click(); await p.waitForTimeout(200);
ok('art: three real versions of b1', (await p.locator('.card img').count()) === 3);
await p.locator('.card').nth(2).locator('button[data-dec="approved"]').click(); await p.waitForTimeout(700);
ok('art: an approved version is locked', await p.locator('.card').nth(2).locator('button[data-dec="rejected"]').isDisabled());
await shot(p, 'desktop-light-art-versions');
await p.context().close();

// ---------------- brand looks (prototype samples): Time Keeper sees only its own
p = await open('phone', 'dark', 'tk~art');
ok('looks: Time Keeper art shows its two looks with samples', JSON.stringify(await p.locator('.card[data-look]').evaluateAll((cs) => cs.map((c) => c.dataset.look))) === JSON.stringify(['swiss_grid', 'dark_keynote'])
  && (await p.locator('.card[data-look] .pv img').count()) === 2);
ok('looks: no Diabetes look on Time Keeper', (await p.locator('.card[data-look="copperplate_engraving"], .card[data-look="silent_film_cards"]').count()) === 0);
ok('phone: no sideways scroll (looks)', await noScroll(p));
await shot(p, 'phone-dark-looks-tk');
await p.locator('.card[data-look="swiss_grid"] button[data-dec="concept_selected"]').click(); await p.waitForTimeout(700);
snap = await api();
ok('looks: choosing a look is recorded as a selection', (snap.looks.timekeeper.find((x) => x.technique === 'swiss_grid').decision || {}).decision === 'concept_selected');
await go(p, 'dh~art~d1');
ok('looks: a Diabetes scene offers its look with the sample, labelled not drawn for it', (await p.locator('.card', { hasText: 'Silent-film' }).locator('.lab').first().textContent()).includes('not drawn for d1'));
await shot(p, 'phone-dark-looks-dh-d1');
await p.context().close();

// ---------------- the remaining screens, both sizes
for (const [h, n] of [['dh~review', 'desktop-dark-home-dh'], ['dh~scene~' + scenes[3].id, 'desktop-dark-scene'], ['tk~voice~3', 'desktop-dark-voice'], ['dh~scenes', 'desktop-dark-scenes'], ['dh~tasks', 'desktop-dark-tasks'], ['dh~style', 'desktop-dark-style'], ['tk~more', 'desktop-dark-more']]) {
  const q = await open('desktop', 'dark', h); await shot(q, n); await q.context().close();
}
for (const [h, n] of [['tk~scenes', 'phone-light-scenes-tk'], ['dh~art~b1', 'phone-light-art'], ['tk~style', 'phone-light-style-tk'], ['dh~style', 'phone-light-style-dh'], ['dh~more', 'phone-light-more']]) {
  const q = await open('phone', 'light', h); ok('phone: no sideways scroll ' + h, await noScroll(q));
  if (h === 'dh~style') words['Style'] = await wc(q); if (h === 'dh~more') words['More'] = await wc(q); if (h === 'dh~art~b1') words['Art'] = await wc(q);
  await shot(q, n); await q.context().close();
}
// ---------------- words on screen, previous page vs this one (same data)
const old = {};
if (oldBase) for (const [label, h] of [['Review (home)', 'dh~watch'], ['Scene review', 'dh~scene~a1'], ['Scenes', 'dh~timeline'], ['All tasks', 'dh~reviews'], ['Listening check', 'tk~reviews'], ['Art', 'dh~art~b1'], ['Style', 'dh~identity'], ['More', 'dh~costs']]) {
  const q = await open('phone', 'dark', h, oldBase); old[label] = await wc(q); await q.context().close();
}
await b.close();
ok('no page errors', errors.length === 0, errors.join(' | '));
fs.writeFileSync(`${out}/results.json`, JSON.stringify(res, null, 1));
fs.writeFileSync(`${out}/voice-playback.json`, JSON.stringify(voice, null, 1));
fs.writeFileSync(`${out}/words.json`, JSON.stringify({ now: words, before: old }, null, 1));
for (const r of res) console.log((r.pass ? 'PASS ' : 'FAIL ') + r.name + (r.pass ? '' : '  (' + r.detail + ')'));
console.log('words on screen (phone):', JSON.stringify({ now: words, before: old }));
const f = res.filter((r) => !r.pass).length; console.log(`${res.length - f}/${res.length} passed`); process.exit(f ? 1 : 0);
