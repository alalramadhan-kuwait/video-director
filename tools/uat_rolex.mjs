// UAT: the Rolex Oyster video, created from an idea through the Studio UI, as the owner would.
//   node tools/uat_rolex.mjs http://127.0.0.1:8767 var/uat PHASE [PHASE...]
// Phases: A B C D E G H I J R  (run in order; state lives on the server, so phases can be re-run separately)
// OWNER actions go through the page (clicks, taps, typing) on an iPhone-sized screen. OPERATOR inputs (research,
// script versions, hooks, art brief) are posted to the API and labelled actor 'writer:claude' / 'art:claude', because
// the studio has no writer or artist of its own. Results: OUT/results.json (append), screenshots OUT/shots/.
import { createRequire } from 'node:module';
import fs from 'node:fs';
const require = createRequire(import.meta.url);
const { chromium, devices } = require('/opt/node22/lib/node_modules/playwright');
const [base, out, ...phases] = process.argv.slice(2);
const SH = `${out}/shots`; fs.mkdirSync(SH, { recursive: true });
const RES = `${out}/results.json`;
const results = fs.existsSync(RES) ? JSON.parse(fs.readFileSync(RES, 'utf8')) : [];
const ok = (stage, name, pass, detail = '') => { results.push({ stage, name, pass: !!pass, detail: String(detail).slice(0, 600), at: new Date().toISOString() }); console.log(`${pass ? 'PASS' : 'FAIL'} [${stage}] ${name}${detail ? ' — ' + String(detail).slice(0, 200) : ''}`); fs.writeFileSync(RES, JSON.stringify(results, null, 1)); };
const C = (f) => JSON.parse(fs.readFileSync(f, 'utf8'));
const SCRIPT = C('uat/rolex/script.json'), HOOKS = C('uat/rolex/hooks.json'), BRIEF = C('uat/rolex/art_brief.json'), RESEARCH = C('research/rolex-oyster.json');
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args: ['--no-proxy-server', '--autoplay-policy=no-user-gesture-required'] });
const iphone = { ...devices['iPhone 13'] }; delete iphone.defaultBrowserType;
const errors = [];
async function page(kind = 'phone', scheme = 'light') {
  const ctx = await b.newContext(kind === 'phone' ? { ...iphone, colorScheme: scheme } : { viewport: { width: 1366, height: 900 }, deviceScaleFactor: 1, colorScheme: scheme });
  await ctx.route((u) => !u.href.startsWith(base), (r) => r.abort());
  const p = await ctx.newPage(); p.on('pageerror', (e) => errors.push(e.message)); p.on('dialog', (d) => d.accept(page.answer || 'ok'));
  return p;
}
const shot = (p, n, full = true) => p.screenshot({ path: `${SH}/${n}.png`, fullPage: full });
const wait = (ms) => new Promise((r) => setTimeout(r, ms));
let PID = fs.existsSync(`${out}/pid`) ? fs.readFileSync(`${out}/pid`, 'utf8').trim() : null;
const state = async () => (await fetch(`${base}/api/studio/${PID}`)).json();
const post = async (action, args, actor = 'writer:claude', rid) => { const r = await fetch(`${base}/api/studio`, { method: 'POST', body: JSON.stringify({ project: PID, action, args, actor, request_id: rid }) }); return { code: r.status, ...(await r.json()) }; };
async function allFit(p) {   // every Studio screen, each freshly loaded (a phone keeps a widened layout across hash changes)
  const wide = [];
  for (const st of ['overview', 'inbox', 'research', 'script', 'hook', 'voice', 'art', 'storyboard', 'draft', 'review', 'gate', 'history']) {
    await go(p, st); await p.reload(); await p.waitForTimeout(600); if (!(await noScroll(p))) wide.push(st); }
  return wide;
}
async function go(p, hash) { await p.goto(`${base}/studio#/p/${PID}/${hash}`); await p.waitForTimeout(700); }
async function untilIdle(label, max = 1800) {
  const t0 = Date.now();
  for (;;) { const s = await state(); const run = s.jobs.filter((j) => j.state === 'running');
    if (!run.length) return { s, secs: (Date.now() - t0) / 1000 };
    if ((Date.now() - t0) / 1000 > max) throw new Error(`${label}: still running after ${max}s`); await wait(2000); }
}
const noScroll = (p) => p.evaluate(() => Math.max(document.documentElement.scrollWidth, innerWidth) <= (matchMedia('(pointer:coarse)').matches ? screen.width : innerWidth) + 1);   // on a phone innerWidth grows with the overflow, so compare with the screen

// =============================================================== A. create project
async function A() {
  const p = await page('phone');
  await p.goto(`${base}/studio`); await p.waitForTimeout(600); await shot(p, 'A1-studio-home');
  await p.click('#newBtn'); await p.waitForTimeout(300);
  await p.fill('#idea', 'The story of the Rolex Oyster and the development of the first waterproof wristwatch.');
  await p.fill('#title', 'Rolex Oyster');
  await p.click('[data-brand="timekeeper"]'); await shot(p, 'A2-new-project-form');
  await p.click('#createBtn'); await p.waitForTimeout(1200);
  PID = p.url().split('/p/')[1]; fs.writeFileSync(`${out}/pid`, PID);
  ok('A', 'project created through the form', !!PID && (await p.textContent('#ptitle')).includes('Rolex Oyster'), PID);
  const s = await state();
  ok('A', 'Time Keeper identity loaded (profile, palette, end card)', s.identity.profile === 'timekeeper-luxury-doc' && s.identity.endcard === 'tk_endcard' && Object.keys(s.identity.palette).every((k) => k.startsWith('tk-')), JSON.stringify(s.identity.palette));
  const txt = await p.textContent('main');
  ok('A', 'no Diabetes History artwork, voice or branding on the page', !/diabetes|fasih|bram|papercut\.js|#E9DCC3/i.test(txt) && !JSON.stringify(s.identity).match(/diabetes|fasih|bram/i), '');
  await p.click('[data-voice="abdullah"]'); await p.waitForTimeout(800);
  const s2 = await state();
  ok('A', 'ElevenLabs final voice chosen: abdullah, recorded as NOT usable until authorized for this film', s2.voice_profile?.name === 'abdullah' && s2.voice_profile.status === 'needs_authorization', s2.voice_profile?.why);
  ok('A', 'voice choice shown on the page with its status', (await p.textContent('#voicechoice')).includes('needs_authorization'));
  await shot(p, 'A3-project-overview-identity');
  // a Diabetes History profile is refused on a Time Keeper project
  const r = await post('set_identity', { profile: 'diabetes-history-sci' }, 'owner');
  ok('A', 'Diabetes History profile refused on this project', r.code === 422, r.reason);
  // reopen: a new browser context, same project
  const p2 = await page('desktop'); await p2.goto(`${base}/studio`); await p2.waitForTimeout(700);
  await p2.click(`[data-project="${PID}"]`); await p2.waitForTimeout(700);
  ok('A', 'project listed and reopened in a fresh session', (await p2.textContent('#ptitle')).includes('Rolex Oyster'));
  await go(p2, 'history'); ok('A', 'version history lists the creation and the voice choice', (await p2.textContent('#hist')).includes('created «Rolex Oyster»') && (await p2.textContent('#hist')).includes('final voice abdullah'));
  await shot(p2, 'A4-history-desktop');
  await p.close(); await p2.close();
}

// =============================================================== B. research + script
async function B() {
  let r = await post('research', { data: RESEARCH }, 'research:claude');
  ok('B', 'research saved with sources (operator)', r.status === 'recorded', JSON.stringify(r.result?.counts));
  const p = await page('phone');
  await go(p, 'research'); await shot(p, 'B1-research');
  ok('B', 'research shows the avoid-claim about "first waterproof watch"', (await p.textContent('#claims')).includes('Rolex invented the first waterproof watch'));
  await p.click('[data-research="approved"]'); await p.waitForTimeout(700);
  ok('B', 'owner approved research in the page', (await state()).research.status === 'approved');
  // v1 from the writer
  r = await post('script_version', { lines: SCRIPT.v1, note: 'first draft', author: 'writer:claude' });
  const crit = r.result.checks.filter((c) => c.code === 'CLAIM_UNSUPPORTED');
  ok('B', 'checker catches the unsupported "first waterproof wristwatch" claim in v1', crit.some((c) => c.line === 'l6'), JSON.stringify(crit.map((c) => c.line)));
  await go(p, 'script/1'); await shot(p, 'B2-script-v1-checks');
  await p.click('#approveScript'); await p.waitForTimeout(700);
  ok('B', 'approving v1 is refused because of the critical claim', (await p.textContent('#toast')).includes('critical'), await p.textContent('#toast'));
  page.answer = SCRIPT.v1_rejection;
  await p.click('[data-sdec="rejected"]'); await p.waitForTimeout(800);
  let s = await state();
  ok('B', 'owner rejected v1 with a reason (kept with the version)', s.scripts[0].status === 'rejected' && s.scripts[0].note_decision.includes('l6'));
  // v2 answers the rejection; v3 has an accidental typo (UAT)
  const v2 = SCRIPT.v1.map((l) => ({ ...l, text: SCRIPT.v2_changes[l.id] || l.text }));
  r = await post('script_version', { lines: v2, note: 'answers the rejection of v1', author: 'writer:claude' });
  ok('B', 'v2 has no critical findings', !r.result.checks.some((c) => c.severity === 'critical'), JSON.stringify(r.result.checks.filter((c) => c.severity !== 'info')));
  const v3 = v2.map((l) => (l.id === SCRIPT.v3_typo.line ? { ...l, text: l.text.replace(SCRIPT.v3_typo.from, SCRIPT.v3_typo.to) } : l));
  r = await post('script_version', { lines: v3, note: 'tightened l6 wording (contains a typo on purpose)', author: 'writer:claude' });
  const sp = r.result.checks.find((c) => c.code === 'SPELLING');
  ok('B', 'intentional typo «فيلسدروف» detected as a spelling problem with a suggestion', sp && sp.word === 'فيلسدروف' && sp.suggestion === 'فيلسدورف', JSON.stringify(sp));
  await go(p, 'script/3'); await shot(p, 'B3-script-v3-typo-detected');
  // highlight the word, explain, request a correction (through the page)
  const w = p.locator('[data-sw="l6"].issue-major').first();
  await w.click(); await p.waitForTimeout(400);
  ok('B', 'tapping the highlighted word opens the flag sheet with the suggestion', (await p.inputValue('#frepl')) === 'فيلسدورف');
  await p.click('[data-fk="spelling"]'); await p.fill('#fnote', 'two letters swapped in the name Wilsdorf');
  await shot(p, 'B4-flag-sheet', false);
  await p.click('#fsave'); await p.waitForTimeout(800);
  s = await state();
  ok('B', 'correction request recorded with word, kind and explanation', s.flags.length === 1 && s.flags[0].word === 'فيلسدروف' && s.flags[0].kind === 'spelling' && s.flags[0].note.includes('swapped'));
  await shot(p, 'B5-correction-request');
  await p.click(`[data-apply="${s.flags[0].flag}"]`); await p.waitForTimeout(1200);
  s = await state();
  const v4 = s.scripts[3];
  ok('B', 'correction made v4 with exactly one word changed', v4 && v4.diff.length === 1 && v4.diff[0].old === 'فيلسدروف' && v4.diff[0].new === 'فيلسدورف', JSON.stringify(v4?.diff));
  const same = Object.entries(s.script_versions[3]).length && s.script_versions[3].every((l, i) => l.id === SCRIPT.v3_typo.line || l.text === s.script_versions[4][i].text);
  ok('B', 'every other line identical between v3 and v4', same);
  ok('B', 'earlier versions preserved unchanged (v1..v3 still readable, v1 rejected, v3 still has the typo)', s.scripts.length === 4 && s.script_versions[3].find((l) => l.id === 'l6').text.includes('فيلسدروف') && s.script_versions[1].find((l) => l.id === 'l6').text.includes('أول ساعة يد'));
  await shot(p, 'B6-script-v4-diff');
  // compare versions in the page
  await p.selectOption('#cmpA', '3'); await p.selectOption('#cmpB', '4'); await p.click('[data-compare]'); await p.waitForTimeout(200);
  ok('B', 'compare view shows the single change', (await p.textContent('#cmpOut')).includes('فيلسدروف') && (await p.textContent('#cmpOut')).includes('فيلسدورف'));
  page.answer = '';
  await p.click('#approveScript'); await p.waitForTimeout(800);
  s = await state();
  ok('B', 'owner approved v4', s.scripts[3].status === 'approved');
  ok('B', 'approved version cannot be decided again (final)', (await post('script_decision', { v: 4, decision: 'rejected', note: 'x' }, 'owner')).code === 422);
  await p.close();
}

// =============================================================== C. hooks
async function C_() {
  const r = await post('hooks', { options: HOOKS.options, recommended: HOOKS.recommended, reasons: HOOKS.reasons, author: 'writer:claude' });
  ok('C', '4 hooks recorded with checks (operator)', r.status === 'recorded' && r.result.options.length === 4, JSON.stringify(r.result.options.map((o) => [o.id, o.checks.length])));
  // art brief is needed for the opening frames
  const ab = await post('art_brief', { brief: BRIEF }, 'art:claude');
  ok('C', 'art brief recorded (operator)', ab.status === 'recorded');
  const p = await page('phone');
  await go(p, 'hook'); await p.click('#hookStills'); await p.waitForTimeout(500);
  const { secs } = await untilIdle('hook stills', 600);
  await go(p, 'hook'); await shot(p, 'C1-hooks');
  const s = await state();
  ok('C', 'each hook shows spoken line, on-screen text and its rendered opening frame', s.hooks.options.every((o) => (s.hooks.stills[o.id] || []).length === 3) && (await p.locator('[data-hook] img').count()) >= 12, `frames drawn in ${secs.toFixed(0)} s`);
  ok('C', 'recommendation with reasons shown', (await p.textContent('main')).includes('Recommended: H1'));
  await p.click('[data-hsel="H1"]'); await p.waitForTimeout(900);
  let st = await state();
  ok('C', 'hook H1 selection recorded; it made script v5 with the hook as the first line', st.hooks.selected === 'H1' && st.scripts[4]?.origin?.hook === 'H1' && st.script_versions[5][0].id === 'h');
  ok('C', 'selecting a hook did not approve the new script version', st.scripts[4].status === 'draft');
  await shot(p, 'C2-hook-selected');
  const payoff = await p.textContent('#payoff');
  ok('C', 'the owner is asked to pick the payoff line (keyword overlap shown only as a hint)', (await p.locator('#payofflines input[type=radio]').count()) === 12, payoff.slice(0, 120));
  await p.click('[data-deliver="delivered"]'); await p.waitForTimeout(500);
  ok('C', '"Delivered" without choosing a line is refused', (await p.textContent('#toast')).includes('Choose the line'));
  await p.check('#payofflines input[value="l13"]'); await p.click('[data-deliver="delivered"]'); await p.waitForTimeout(700);
  await go(p, 'script/5'); await p.click('#approveScript'); await p.waitForTimeout(800);
  st = await state();
  ok('C', 'owner confirmed the payoff (l13) and approved v5', st.hooks.delivery?.decision === 'delivered' && st.hooks.delivery.line === 'l13' && st.scripts[4].status === 'approved');
  await p.close();
}

// =============================================================== D. draft voice
async function D() {
  const p = await page('phone');
  await go(p, 'voice'); await shot(p, 'D1-voice-before');
  ok('D', 'draft voice is labelled as draft gTTS, not the final voice', (await p.textContent('.banner-draft')).includes('does not prove'));
  const s0 = await state();
  ok('D', 'narration-ready text comes from the approved script v5', s0.narration.script_v === 5 && s0.narration.lines.length === 13);
  await p.click('#makeVoice'); await p.waitForTimeout(3000);
  await go(p, 'overview'); await shot(p, 'D2-progress-while-voicing');
  const runTxt = await p.textContent('#running').catch(() => '');
  ok('D', 'progress shows the running task with counted lines', /draft voice/.test(runTxt) && /\/13/.test(runTxt), runTxt.slice(0, 120));
  for (let i = 0; i < 120 && Object.keys((await state()).voice.takes).length < 3; i++) await wait(1000);   // let a few lines finish
  // INTERRUPTED TASK: the server is killed mid-run by the harness (phase D2 continues after restart)
  fs.writeFileSync(`${out}/D-interrupt`, String(Date.now()));
  await p.close();
}
async function D2() {
  const p = await page('phone');
  await go(p, 'overview'); await shot(p, 'D3-after-restart-interrupted');
  let s = await state();
  const j = s.jobs.find((x) => x.kind === 'voice');
  ok('R', 'after a server restart the voice task shows as interrupted (not done, not running)', j?.state === 'interrupted', j?.state);
  const made = Object.keys(s.voice.takes).length;
  ok('R', 'lines finished before the restart are kept', made > 0 && made < 13, `${made} takes kept`);
  await p.click(`[data-resume="${j.id}"]`); await p.waitForTimeout(1500);
  const { secs } = await untilIdle('voice', 1500);
  s = await state();
  ok('R', 'resume finished the remaining lines only', Object.keys(s.voice.takes).length === 13 && s.jobs.filter((x) => x.kind === 'voice').some((x) => x.state === 'finished'), `${Object.keys(s.voice.takes).length} takes, ${secs.toFixed(0)} s`);
  const runs = s.runs.filter((r) => r.stage === 'voice');
  ok('I', 'measured time recorded per voice run', runs.every((r) => r.elapsed_s > 0), runs.map((r) => `${r.state}:${r.units_done}/${r.units_total}:${r.elapsed_s}s`).join(' '));
  await go(p, 'voice'); await shot(p, 'D4-voice-takes');
  ok('D', 'every line shows a waveform and its words', (await p.locator('svg.wave').count()) === 13 && (await p.locator('[data-vw]').count()) > 120);
  // tap a word: the word plays (playhead/now highlight) and the sheet opens
  const tid = s.voice.by_line['l9'][0];
  const words9 = s.voice.takes[tid].words.map((w) => w.w);
  const wi = words9.findIndex((w) => w.includes('غلايتسه'));
  await p.locator(`[data-vw="${tid}"][data-wi="${wi}"]`).scrollIntoViewIfNeeded();
  await p.click(`[data-vw="${tid}"][data-wi="${wi}"]`); await p.waitForTimeout(250);
  const playing = await p.evaluate(() => ({ t: document.querySelector('audio') ? 0 : 1 }));
  await p.waitForTimeout(900);
  for (let i = 0; i < 30 && !(await p.textContent('#wheard')).includes('played'); i++) await p.waitForTimeout(100);
  await shot(p, 'D5-word-sheet', false);
  await p.click('[data-vk="vowel"]');
  await p.fill('#vnote', 'Gleitze: the draft voice stresses the wrong syllable; it should sound like «غلايْتْسَه» (German ei = اي).');
  await p.fill('#vrespell', 'غْلايْتْسَهْ');
  await p.click('#vsave'); await p.waitForTimeout(800);
  s = await state();
  const vf = s.voice.flags[0];
  ok('D', 'mispronounced word flagged with kind, note and suggested reading', vf && vf.word.includes('غلايتسه') && vf.kind === 'vowel' && vf.line === 'l9', JSON.stringify(vf));
  await go(p, 'voice'); await shot(p, 'D6-voice-flag-open');
  const before = Object.fromEntries(Object.entries(s.voice.by_line).map(([k, v]) => [k, v[v.length - 1]]));
  await p.click(`[data-vfix="${vf.vflag}"]`); await p.waitForTimeout(1500);
  const r2 = await untilIdle('voice fix', 600);
  s = r2.s;
  const fixJob = s.jobs.filter((x) => x.kind === 'voice').pop();
  ok('D', 'correction applied to l9 only: a new take, the pronunciation rule recorded', s.voice.by_line.l9.length === 2 && s.voice.rules.length === 1 && s.voice.rules[0].lines[0] === 'l9', JSON.stringify(s.voice.rules[0]));
  ok('D', 'no other line got a new take (ids and audio hashes compared before/after)', fixJob.out?.others_unchanged === true && Object.entries(before).every(([k, v]) => k === 'l9' || s.voice.by_line[k].slice(-1)[0] === v), JSON.stringify({ unchanged: fixJob.out?.others_unchanged, checked: fixJob.out?.others_checked }));
  const nt = s.voice.takes[s.voice.by_line.l9[1]];
  ok('D', 'the new take was sent the corrected reading', nt.spoken.includes('غْلايْتْسَهْ') && nt.supersedes === s.voice.by_line.l9[0], nt.spoken);
  await go(p, 'voice/l9'); await shot(p, 'D7-compare-old-new');
  ok('D', 'old and corrected takes are shown side by side', (await p.locator('[data-compare="l9"] .take').count()) === 2);
  // try approving the new take without listening (refused), then listen and approve; reject the old one
  const newT = s.voice.by_line.l9[1], oldT = s.voice.by_line.l9[0];
  await p.click(`[data-tdec="approved"][data-t="${newT}"]`); await p.waitForTimeout(600);
  ok('D', 'approving without listening is refused', (await p.textContent('#toast')).includes('listen'), await p.textContent('#toast'));
  await p.click(`[data-tplay="${oldT}"]`); await p.waitForTimeout(nt.seconds * 1000 + 1500);
  await p.click(`[data-tplay="${newT}"]`); await p.waitForTimeout(nt.seconds * 1000 + 1500);
  await p.click(`[data-tdec="rejected"][data-t="${oldT}"]`); await p.waitForTimeout(700);
  await p.click(`[data-tdec="approved"][data-t="${newT}"]`); await p.waitForTimeout(700);
  s = await state();
  ok('D', 'old take rejected, corrected take approved after both were heard', s.voice.takes[oldT].status === 'rejected' && s.voice.takes[newT].status === 'approved');
  await shot(p, 'D8-take-decided');
  // listen to every other line and approve it (real-time playback in the page)
  await go(p, 'voice');
  for (const ln of Object.keys(s.voice.by_line)) {
    const t = s.voice.takes[s.voice.by_line[ln].slice(-1)[0]];
    if (t.status !== 'candidate') continue;
    await p.click(`[data-tplay="${t.id}"]`); await p.waitForTimeout(t.seconds * 1000 + 900);
    await p.click(`[data-tdec="approved"][data-t="${t.id}"]`); await p.waitForTimeout(500);
  }
  s = await state();
  const cur = Object.values(s.voice.by_line).map((ids) => s.voice.takes[ids[ids.length - 1]].status);
  ok('D', 'all 13 current takes approved after listening; decisions saved', cur.every((x) => x === 'approved'), cur.join(','));
  const pv = await page('desktop'); await pv.goto(`${base}/studio#/p/${PID}/voice`); await pv.waitForTimeout(900);
  ok('D', 'decisions appear after reopening in another session', (await pv.locator('.pill.s-ok').count()) >= 13);
  await shot(pv, 'D9-voice-desktop'); await pv.close();
  await p.close();
}

// =============================================================== E/F. art
async function E() {
  const p = await page('phone');
  await go(p, 'art'); await p.click('#support summary'); await shot(p, 'E1-support-matrix');
  const sup = (await state()).support;
  ok('E', 'support matrix lists supported, paid and to-build techniques', sup.some((x) => x.level === 'paid tool') && sup.some((x) => x.level === 'needs implementation') && sup.some((x) => x.level.startsWith('supported')), sup.map((x) => `${x.id}:${x.level}`).join(' | '));
  for (const sc of ['l2', 'l5', 'l9', 'l11']) {
    await go(p, 'art'); await p.click(`[data-scene-run="${sc}"]`); await p.waitForTimeout(800);
    await untilIdle('concepts ' + sc, 900);
  }
  let s = await state();
  await go(p, 'art'); await shot(p, 'E2-concepts');
  const cs = Object.values(s.art.concepts);
  ok('E', 'several genuinely different techniques per scene rendered by the engine', ['l2', 'l5', 'l9', 'l11'].every((sc) => new Set(s.art.by_scene[sc].map((id) => s.art.concepts[id].technique)).size >= 2), cs.map((c) => `${c.id}:${c.support}`).join(' | '));
  ok('E', 'product macro and archival photo concepts are BLOCKED for missing licensed photos (no fabricated image)', cs.filter((c) => ['product_macro', 'archival_collage'].includes(c.technique)).every((c) => c.support === 'blocked: missing asset'));
  // full-screen viewer
  const first = p.locator('[data-concept="l9-map"] img.still');
  await first.click(); await p.waitForTimeout(500);
  ok('F', 'concept opens full-screen', await p.isVisible('#viewer'));
  await shot(p, 'F1-fullscreen', false);
  await p.click('[data-vclose]');
  // select ≠ approve
  await p.click('[data-asel="l9-map"]'); await p.waitForTimeout(700);
  s = await state();
  ok('F', 'selecting a concept records a selection, not an approval', s.art.selected.l9 === 'l9-map' && !s.art.approved.l9);
  // request modification, review the revision, approve that version
  await p.click('[data-amod="l9-map"]'); await p.waitForTimeout(300);
  await p.click('[data-mod="zoom:1.18"]');
  await shot(p, 'F2-modification-sheet', false);
  await p.click('[data-msave="l9-map"]'); await p.waitForTimeout(800);
  await untilIdle('revision', 600);
  s = await state();
  const c9 = s.art.concepts['l9-map'];
  ok('F', 'requested revision produced v2 (v1 kept)', c9.versions.length === 2 && c9.versions[1].changes.zoom === '1.18' && c9.versions[0].stills.length === 2);
  ok('F', 'v2 really looks different from v1 (closer map), not a copy', c9.versions[1].stills.every((x, i) => x !== c9.versions[0].stills[i]) && !c9.versions[1].no_visible_change);
  await go(p, 'art'); await p.locator('[data-cmp="l9-map"]').scrollIntoViewIfNeeded(); await shot(p, 'F3-revision', false);
  ok('F', 'v1 and v2 of the revised concept are shown side by side as images', (await p.locator('[data-cmp="l9-map"] img').count()) === 2);
  await p.click('[data-aok="l9-map"]'); await p.waitForTimeout(700);
  s = await state();
  ok('F', 'owner approved the specific version v2', s.art.approved.l9?.version === 2 && s.art.concepts['l9-map'].versions[1].status === 'approved');
  // rejected art concept path (failure recovery): select the timeline for l2, approve, then withdraw
  await p.click('[data-arej="l5-kinetic_type"]'); await p.waitForTimeout(600);
  s = await state();
  ok('R', 'rejecting an art concept is recorded and the concept can no longer be approved', s.art.concepts['l5-kinetic_type'].versions[0].status === 'rejected' && (await post('art_decision', { concept: 'l5-kinetic_type', version: 1, decision: 'approved' }, 'owner')).code === 422);
  await p.click('[data-asel="l5-paper_cut"]'); await p.waitForTimeout(500);
  await p.click('[data-aok="l5-paper_cut"]'); await p.waitForTimeout(600);
  page.answer = 'the crown drawing explains the patent better';
  await p.click('[data-awd="l5-paper_cut"]'); await p.waitForTimeout(600); page.answer = '';
  s = await state();
  ok('R', 'an approval can be withdrawn with a reason; the scene is open again and the history keeps both', !s.art.approved.l5 && s.art.concepts['l5-paper_cut'].versions[0].status === 'withdrawn' && s.history.some((h) => h.summary.includes('l5-paper_cut v1 withdrawn')));
  for (const [sc, cid] of [['l2', 'l2-animated_timeline'], ['l5', 'l5-technical_illustration'], ['l11', 'l11-paper_cut']]) {
    await p.click(`[data-asel="${cid}"]`); await p.waitForTimeout(500); await p.click(`[data-aok="${cid}"]`); await p.waitForTimeout(600);
  }
  s = await state();
  ok('F', 'four scenes have approved art', ['l2', 'l5', 'l9', 'l11'].every((x) => s.art.approved[x]), JSON.stringify(s.art.approved));
  ok('F', 'a withdrawn version cannot be approved again without a new version', (await post('art_decision', { concept: 'l5-paper_cut', version: 1, decision: 'approved' }, 'owner')).code === 422);
  await go(p, 'art'); await shot(p, 'F4-art-approved');
  await p.close();
}

// =============================================================== G. storyboard + draft
async function G() {
  const p = await page('phone');
  await go(p, 'storyboard'); await p.click('[data-build]'); await p.waitForTimeout(1200);
  let s = await state();
  const sb = s.storyboard;
  const apv = s.scripts.filter((x) => x.status === 'approved').slice(-1)[0].v;
  ok('G', `storyboard built from the latest approved script (v${apv}) with 13 scenes + end card`, sb.script_v === apv && sb.scenes.length === 13 && sb.endcard === 'timekeeper', `${s.storyboards.slice(-1)[0].seconds}s`);
  const l9 = sb.scenes.find((x) => x.id === 'l9');
  ok('G', `approved art (l9 map v${s.art.approved.l9.version}) appears in its storyboard scene`, l9.technique === 'map' && l9.concept === 'l9-map' && l9.art_version === s.art.approved.l9.version && s.art.approved.l9.version >= 2, `v${l9.art_version}`);
  ok('G', 'scene durations follow the approved takes', sb.scenes.every((x) => { const t = s.voice.takes[x.take]; return t && Math.abs(x.dur - (0.15 + t.seconds + 0.45)) < 0.02 && x.status.voice === 'approved'; }));
  await go(p, 'storyboard'); await shot(p, 'G1-storyboard');
  const warn = await p.textContent('#sbwarn').catch(() => '');
  ok('G', 'storyboard says which scenes are not individually approved (brief defaults, the Wilsdorf placeholder)', /not reviewed/.test(warn) && /PLACEHOLDER/.test(warn) && !(await p.textContent('main')).includes('everything approved'));
  ok('G', 'the storyboard step is not Done until the owner approves it', s.steps.find((x) => x.id === 'storyboard').state === 'waiting_review');
  await p.click('[data-sbdec="approved"]'); await p.waitForTimeout(700);
  ok('G', 'owner approved the storyboard as shown', (await state()).storyboards.slice(-1)[0].decision === 'approved');
  // FAILED RENDER (injected) then a successful one
  await fetch(`${base}/api/studio/_test`, { method: 'POST', body: JSON.stringify({ fail_next: { render: 'simulated renderer crash (UAT)' } }) });
  await go(p, 'draft'); await p.click('#renderBtn'); await p.waitForTimeout(2500);
  await untilIdle('failed render', 120);
  await go(p, 'draft');
  s = await state();
  ok('R', 'a failed render is shown as failed with its error; nothing approved changed', s.jobs.filter((j) => j.kind === 'render').pop().state === 'failed' && (await p.textContent('#blockers').catch(async () => { await go(p, 'overview'); return p.textContent('#blockers'); })).includes('failed'));
  await go(p, 'overview'); await shot(p, 'G2-render-failed-blocker');
  await go(p, 'draft'); await p.click('#renderBtn'); await p.waitForTimeout(3000);
  let etaSeen = null, frameUnits = 0;
  for (let i = 0; i < 1200; i++) {
    const v = await state(); const fr = v.running.find((r) => r.task.startsWith('draft frames'));
    if (fr) { frameUnits = fr.units_done; if (fr.eta_s != null && !etaSeen) { etaSeen = fr; await go(p, 'overview'); await shot(p, 'G3-render-progress-eta'); } }
    if (!v.jobs.some((j) => j.state === 'running')) break; await wait(2000);
  }
  ok('I', 'render progress counts frame steps and shows an ETA only once 3 equal steps were measured', etaSeen && etaSeen.units_done >= 3, etaSeen ? `${etaSeen.units_done}/10 steps, eta ${etaSeen.eta_s}s (${etaSeen.eta_reason})` : 'no ETA seen');
  const { secs } = await untilIdle('render', 2400);
  s = await state();
  const r = s.renders.filter((x) => x.state === 'ok').pop();
  ok('G', 'draft rendered with the free local engine', !!r, r ? `${r.id} ${r.seconds}s ${r.size_mb}MB in ${r.render_s}s (job ${secs.toFixed(0)}s)` : JSON.stringify(s.renders.slice(-1)));
  await go(p, 'draft'); await shot(p, 'G4-draft-player');
  // seeking to the end is not watching
  await p.evaluate(async () => { const v = document.querySelector('video[data-film]'); v.muted = true; await new Promise((ok) => { if (v.readyState >= 1) ok(); else v.addEventListener('loadedmetadata', ok, { once: true }); }); v.currentTime = v.duration - 1; await v.play(); await new Promise((ok) => v.addEventListener('ended', ok, { once: true })); });
  const r0 = (await state()).renders.filter((x) => x.state === 'ok').pop();
  await p.click(`[data-rdec="approved_as_draft"][data-r="${r0.id}"]`); await p.waitForTimeout(700);
  ok('R', 'approving a draft after jumping to its end is refused (skipping is not watching)', (await p.textContent('#toast')).includes('does not count') && !(await state()).renders.find((x) => x.id === r0.id).decision, await p.textContent('#toast'));
  await go(p, 'draft');
  const playable = await p.evaluate(async () => { const v = document.querySelector('video[data-film]'); v.muted = true; await v.play(); await new Promise((r) => setTimeout(r, 2500)); const t = v.currentTime; v.pause(); return { t, src: v.currentSrc.split('.').pop(), w: v.videoWidth }; });
  ok('G', 'the latest draft actually plays in the page', playable.t > 1.5, JSON.stringify(playable));
  // muted playback is not watching (audit round 2): the whole film at 2x with the sound off, then try to approve
  await go(p, 'draft');
  await p.evaluate(() => { const v = document.querySelector('video[data-film]'); v.muted = true; v.currentTime = 0; v.playbackRate = 2; return v.play(); });
  await p.waitForTimeout((r.seconds / 2) * 1000 + 3000);
  await p.click(`[data-rdec="approved_as_draft"][data-r="${r.id}"]`); await p.waitForTimeout(700);
  ok('R', 'watching the whole draft muted does not count; approval refused', (await p.textContent('#toast')).includes('does not count') && !(await state()).renders.find((x) => x.id === r.id).decision, await p.textContent('#toast'));
  // watch: audible playback at 2x in the page (the harness cannot sit through it at 1x every time; recorded as such)
  await go(p, 'draft');
  await p.click('h2').catch(() => p.click('body')); await p.evaluate(() => { const v = document.querySelector('video[data-film]'); v.muted = false; v.volume = 1; v.currentTime = 0; v.playbackRate = 2; return v.play(); });   // audible, as an owner watches it
  await p.waitForTimeout((r.seconds / 2) * 1000 + 3000);
  await p.click(`[data-rdec="approved_as_draft"][data-r="${r.id}"]`); await p.waitForTimeout(700);
  s = await state();
  ok('G', 'draft approved as DRAFT after it was played through (2x in the harness)', s.renders.find((x) => x.id === r.id).decision === 'approved_as_draft');
  await p.close();
}

// =============================================================== H. review
async function H() {
  const p = await page('phone');
  await go(p, 'review'); await p.click('[data-run="run_review"]'); await p.waitForTimeout(1500);
  await untilIdle('review', 1200);
  let s = await state();
  await go(p, 'review'); await shot(p, 'H1-review-findings');
  const fs_ = Object.values(s.review.findings);
  ok('H', 'review ran on the draft and recorded findings with scene, timecode, evidence and fix', fs_.every((f) => f.evidence && f.recommendation && f.severity), `${fs_.length} findings: ` + fs_.map((f) => `${f.code}@${f.scene}`).join(', '));
  fs.writeFileSync(`${out}/clean-review.json`, JSON.stringify(fs_, null, 1));
  await p.close();
}
async function H2() {   // decide on findings (after the defect copy test, which runs from Python)
  const p = await page('phone');
  let s = await state();
  const fs_ = Object.values(s.review.findings).filter((f) => !f.decision);
  await go(p, 'review');
  if (fs_.length) {
    const a = fs_[0];
    const snap = (x) => JSON.stringify({ art: x.art.approved, takes: Object.fromEntries(Object.entries(x.voice.takes).map(([k, t]) => [k, [t.status, t.audio]])), sb: x.storyboards.map((b) => b.file), renders: x.renders.map((r) => [r.id, r.file, r.decision]) });
    const before = snap(s);
    await p.click(`[data-fdec="accepted"][data-f="${a.id}"]`); await p.waitForTimeout(700);
    s = await state();
    ok('H', 'accepting a finding creates a correction task', s.fix_tasks.some((t) => t.finding === a.id && t.status === 'open'), a.code);
    ok('H', 'accepting did not change approved art, takes, storyboards or renders', snap(s) === before);
  }
  let triedEmpty = false;
  for (const f of fs_.slice(1)) {
    if (!triedEmpty) { triedEmpty = true; await p.click(`[data-fdec="dismissed"][data-f="${f.id}"]`); await p.waitForTimeout(500);
      const t = await p.textContent('#toast'); ok('H', 'dismiss without a reason is refused', t.includes('why') && !(await state()).review.findings[f.id].decision, t); }
    await p.fill(`[data-fnote="${f.id}"]`, 'checked on the draft: acceptable for this draft'); await p.click(`[data-fdec="dismissed"][data-f="${f.id}"]`); await p.waitForTimeout(500);
  }
  s = await state();
  ok('H', 'dismissed findings stay in the review history with their reason', Object.values(s.review.findings).filter((f) => f.decision === 'dismissed').every((f) => f.decision_note));
  await go(p, 'review'); await shot(p, 'H3-findings-decided');
  await p.close();
}

// =============================================================== I. progress dashboard
async function I() {
  const p = await page('phone');
  await go(p, 'overview'); await shot(p, 'I1-overview-phone');
  const s = await state();
  ok('I', 'current stage shown matches the first unapproved step', (await p.textContent('#nextBtn')).includes(s.steps.find((x) => x.id === s.stage).name), s.stage);
  ok('I', 'inbox card and counts shown on the overview', !!(await p.$('#inboxCard')) && (await p.textContent('#inbox')).includes('Findings'));
  ok('I', 'the latest draft is on the project home and plays', await p.evaluate(async () => { const v = document.querySelector('#homefilm video'); if (!v) return false; v.muted = true; await v.play(); await new Promise((r) => setTimeout(r, 1500)); return v.currentTime > 0.8; }));
  ok('I', 'scene strip shows every scene with voice/art/findings state', (await p.locator('[data-scenechip]').count()) === 13);
  ok('I', 'measured times table lists finished tasks with units and time', (await p.locator('#timings tr').count()) > 3);
  await go(p, 'inbox'); await shot(p, 'I3-inbox');
  const groups = await p.locator('[data-group]').evaluateAll((g) => g.map((x) => x.dataset.group));
  ok('I', 'one inbox lists every outstanding decision, grouped (the open correction task from the review is there)', s.inbox_groups.length === groups.length && s.inbox_groups.every((g) => groups.includes(g.key)) && groups.includes('review'), groups.join(','));
  const wide = await allFit(p);
  ok('I', 'no screen scrolls sideways on an iPhone (every Studio screen checked)', wide.length === 0, wide.join(',') || 'all fit');
  await go(p, 'overview');
  const d = await page('desktop'); await d.goto(`${base}/studio#/p/${PID}`); await d.waitForTimeout(800); await shot(d, 'I2-overview-desktop');
  ok('I', 'desktop overview renders', (await d.textContent('#ptitle')).includes('Rolex'));
  await d.close(); await p.close();
}

// =============================================================== J. final gate
async function J() {
  const p = await page('phone');
  const desk = await page('desktop'); await desk.goto(`${base}/studio#/p/${PID}/inbox`); await desk.waitForTimeout(1200);
  const hadGate = await desk.$('[data-group="gate"]');
  await go(p, 'gate'); await p.click('[data-gplan]'); await p.waitForTimeout(1500);
  for (let i = 0; i < 20 && !(await desk.$('[data-group="gate"]')); i++) await desk.waitForTimeout(500);
  ok('R', 'approval sync: the plan built on the phone shows up in the open desktop inbox without a reload', !hadGate && !!(await desk.$('[data-group="gate"]')));
  await shot(desk, 'J0-desktop-inbox-synced'); await desk.close();
  let s = await state();
  const g = s.gate.plan;
  await go(p, 'gate'); await shot(p, 'J1-final-plan');
  const appr = s.script_versions[5];
  ok('J', 'the final gate shows the approved draft film next to the plan', !!(await p.$('#gatefilm video')) && (await p.textContent('#gatefilm')).includes('approved_as_draft'));
  ok('J', 'plan shows the exact approved narration text per line', g.items.length === 13 && g.items.every((i, k) => i.provider_input === appr[k].text), '');
  ok('J', 'plan shows the selected voice and model', g.voice.name === 'abdullah' && g.voice.model === 'eleven_multilingual_v2' && (await p.textContent('#gplan')).includes('eleven_multilingual_v2'));
  ok('J', 'billable characters calculated', g.chars_total === appr.reduce((n, l) => n + l.text.length, 0), `${g.chars_total} chars`);
  ok('J', 'blockers listed (voice not authorized for this film, paid disabled, budget, proposed names)', ['not authorized', 'approved for royal-oak', 'disabled', 'budget', 'proposed'].every((k) => g.blockers.join(' ').includes(k) || (k === 'not authorized' && g.blockers.join(' ').includes('abdullah'))), g.blockers.join(' | '));
  // the owner's own decisions, in the page
  await p.fill('#gvnote', 'owner: Abdullah approved for the Rolex Oyster film'); await p.click('[data-gvoice]'); await p.waitForTimeout(700);
  for (const t of (await state()).research_terms) { await go(p, 'gate'); await p.click(`[data-term="${t.ar}"][data-tdecision="${t.default === 'latin' ? 'latin' : 'arabic'}"]`); await p.waitForTimeout(400); }
  await go(p, 'gate'); await p.fill('#gbudget', String(g.chars_total + 400)); await p.click('[data-gbudget]'); await p.waitForTimeout(600);
  await go(p, 'gate');
  ok('J', 'the plan is marked out of date after the owner\'s decisions', !!(await p.$('#gstale')));
  await p.click('[data-gplan]'); await p.waitForTimeout(1500);
  s = await state(); const g2 = s.gate.plan;
  ok('J', 'after the owner\'s decisions only the open correction task (from the accepted review finding, closed in K) and the environment lock block paid narration', g2.blockers.length === 2 && g2.blockers.some((b) => /correction task/.test(b)) && g2.blockers.some((b) => b.includes('disabled in this environment')), g2.blockers.join(' | '));
  ok('J', 'approved names go to the final voice in Latin letters (as Time Keeper does)', g2.items.some((i) => i.provider_input.includes('Rolex')) && g2.chars_total !== g.chars_total, `${g.chars_total} → ${g2.chars_total} chars`);
  await go(p, 'gate'); await shot(p, 'J1b-gate-after-owner-decisions');
  const gh = g2;
  await p.waitForTimeout(1000); await p.locator('#gconfirm').scrollIntoViewIfNeeded(); await p.fill('#gconfirm', String(gh.chars_total));
  await p.locator(`[data-gauth="${gh.hash}"]`).click(); await p.waitForTimeout(800);
  ok('J', 'owner authorization refused: paid generation is locked in this workspace', (await p.textContent('#toast')).includes('disabled'), await p.textContent('#toast'));
  await p.click('[data-gen]'); await p.waitForTimeout(800);
  ok('J', 'pressing "Generate final voice now" is refused', (await p.textContent('#toast')).includes('cannot be started'));
  const r = await post('final_generate', {}, 'owner');
  ok('J', 'direct API call for paid generation refused', r.code === 422, r.reason);
  s = await state();
  ok('J', 'refused attempts are kept', s.gate.attempts.length >= 3);
  await go(p, 'gate'); await shot(p, 'J2-gate-refused');
  { const w = await allFit(p); ok('J', 'still no sideways scroll on any screen after the owner\'s notes and decisions', w.length === 0, w.join(',') || 'all fit'); }
  await p.close();
}

// =============================================================== R. recovery extras
async function R() {
  const p = await page('phone');
  // page refresh during review: open the flag sheet, reload, nothing half-saved
  await go(p, 'voice/l2');
  const s0 = await state();
  const t = s0.voice.by_line.l2.slice(-1)[0];
  await p.click(`[data-vw="${t}"][data-wi="1"]`); await p.waitForTimeout(500);
  await p.reload(); await p.waitForTimeout(800);
  const s1 = await state();
  ok('R', 'refresh in the middle of flagging saves nothing half-done and loses nothing', s1.voice.flags.length === s0.voice.flags.length && s1.history.length === s0.history.length);
  // duplicate approval submission: same request id twice; and two fast taps
  const rid = 'dup-' + Date.now(); const fid = Object.values(s0.review.findings).find((f) => !f.decision);
  const a1 = await post('flag_word', { v: 5, line: 'l12', wi: 0, kind: 'other', note: 'duplicate test' }, 'owner', rid);
  const a2 = await post('flag_word', { v: 5, line: 'l12', wi: 0, kind: 'other', note: 'duplicate test' }, 'owner', rid);
  ok('R', 'the same submission twice is recorded once (duplicate)', a1.status === 'recorded' && a2.status === 'duplicate', `${a1.status}/${a2.status}`);
  await post('dismiss_flag', { flag: a1.result.flag, note: 'test only' }, 'owner');
  const [x1, x2] = await Promise.all([post('script_decision', { v: 5, decision: 'approved' }, 'owner'), post('script_decision', { v: 5, decision: 'approved' }, 'owner')]);
  ok('R', 'a second approval of an approved version is refused, not double-counted', [x1.code, x2.code].every((c) => c === 422));
  // a file appearing on disk never approves anything
  const blobDir = `var/dashboard-uat/studio/${PID}/blobs`; const s2 = await state();
  fs.writeFileSync(`${blobDir}/zz-dropped-approved-take.mp3`, 'ID3 a file is not a decision'); fs.writeFileSync(`${blobDir}/zz-final.mp4`, 'not a render');
  const s3 = await state();
  ok('R', 'a file dropped into the project changes no status (statuses come only from decisions)', JSON.stringify(s2.steps) === JSON.stringify(s3.steps) && JSON.stringify(s2.renders) === JSON.stringify(s3.renders) && Object.keys(s2.voice.takes).length === Object.keys(s3.voice.takes).length);
  fs.unlinkSync(`${blobDir}/zz-dropped-approved-take.mp3`); fs.unlinkSync(`${blobDir}/zz-final.mp4`);
  // decisions that must not flip silently
  const hd = await post('hook_delivery', { decision: 'not_delivered' }, 'owner');
  const rd = await post('research_decision', { decision: 'changes_requested' }, 'owner');
  ok('R', 'contradictory second decisions are refused (hook payoff, research)', hd.code === 422 && rd.code === 422, `${hd.reason} | ${rd.reason}`);
  // invalid input
  const bad = await post('flag_word', { v: 5, line: 'l2', wi: 999, kind: 'spelling' }, 'owner');
  ok('R', 'invalid word index refused', bad.code === 422, bad.reason);
  await p.close();
}

async function DW() {   // word tap, measured: which words light up while the tapped word plays, and when the sheet says "played"
  const p = await page('phone'); const s = await state();
  const tid = s.voice.by_line.l7.slice(-1)[0]; const t = s.voice.takes[tid]; const wi = 5; const w = t.words[wi];
  await go(p, 'voice/l7'); const t0 = Date.now();
  await p.click(`[data-vw="${tid}"][data-wi="${wi}"]`);
  const lit = new Set(); let playedAt = null;
  for (let i = 0; i < 40; i++) { await p.waitForTimeout(100);
    (await p.evaluate(() => [...document.querySelectorAll('.wd.now')].map((e) => e.textContent))).forEach((x) => lit.add(x));
    if (!playedAt && (await p.textContent('#wheard')).includes('played')) playedAt = Date.now() - t0; }
  ok('D', 'tapping a word plays that word (and only its neighbours at the edges) and the sheet confirms it was played',
     lit.has(w.w) && lit.size <= 3 && playedAt != null, `word «${w.w}» ${w.s}-${w.e}s; highlighted: ${[...lit].join(' | ')}; "played" after ${playedAt} ms`);
  await shot(p, 'D5b-word-tap-l7', false); await p.close();
}
async function K() {   // a review finding accepted → fixed → re-rendered → re-reviewed → task closed → plan rebuilt
  let s = await state();
  const task = s.fix_tasks.find((t) => t.status === 'open');
  ok('K', 'an open correction task exists from the accepted finding', !!task, JSON.stringify(task));
  if (!task) return;
  const before = s.renders.filter((r) => r.state === 'ok').pop();
  // the art operator fixes the hook visual: the belief is attributed on screen too («يقولون»), so it reads right on mute
  const fixed = JSON.parse(JSON.stringify(BRIEF));
  const lines = [{ text: 'يقولون:', size: 64, at: 0.0, in: 'slam' }, { text: 'أول ساعة', size: 92, at: 0.1, in: 'slam' }, { text: 'مقاومة للماء؟', size: 92, at: 0.3, in: 'slam' }];
  fixed.scenes.h.concepts.kinetic_type = { ...fixed.scenes.h.concepts.kinetic_type, lines, y: 380, stamp: { text: 'ليس تمامًا', at: 1.2, y: 860 } };
  fixed.hook_visuals.H1.params = { ...fixed.hook_visuals.H1.params, lines, y: 380, stamp: { text: 'ليس تمامًا', at: 1.2, y: 860 } };
  const r = await post('art_brief', { brief: fixed }, 'art:claude');
  ok('K', 'operator recorded the corrected art brief (hook text attributed on screen)', r.status === 'recorded');
  const p = await page('phone');
  await go(p, 'storyboard'); await p.click('[data-build]'); await p.waitForTimeout(1200);
  await go(p, 'storyboard'); await p.click('[data-sbdec="approved"]'); await p.waitForTimeout(700);
  await go(p, 'draft'); await p.click('#renderBtn'); await p.waitForTimeout(3000);
  await untilIdle('re-render', 2400);
  s = await state();
  const after = s.renders.filter((x) => x.state === 'ok').pop();
  ok('K', 'a new draft was rendered after the fix; the old one is kept', after.id !== before.id && s.renders.some((x) => x.id === before.id), `${before.id} → ${after.id}`);
  await go(p, 'draft');
  await p.click('h2').catch(() => p.click('body')); await p.evaluate(() => { const v = document.querySelector('video[data-film]'); v.muted = false; v.volume = 1; v.playbackRate = 2; return v.play(); });   // audible, as an owner watches it
  await p.waitForTimeout((after.seconds / 2) * 1000 + 3000);
  await p.click(`[data-rdec="approved_as_draft"][data-r="${after.id}"]`); await p.waitForTimeout(700);
  await go(p, 'review'); await p.click('[data-run="run_review"]'); await p.waitForTimeout(1500); await untilIdle('re-review', 1200);
  s = await state();
  const last = s.review.runs[s.review.runs.length - 1];
  const fs2 = Object.values(s.review.findings).filter((f) => f.run === last.id);
  ok('K', 're-review of the corrected draft: the accepted finding is gone', !fs2.some((f) => f.code === 'CLAIM_ON_SCREEN'), fs2.map((f) => f.code).join(',') || 'no findings');
  await go(p, 'review'); await p.click(`[data-fixdone="${task.id}"]`); await p.waitForTimeout(700);
  for (const f of fs2) { await p.fill(`[data-fnote="${f.id}"]`, 'checked on the corrected draft'); await p.click(`[data-fdec="dismissed"][data-f="${f.id}"]`); await p.waitForTimeout(500); }
  await shot(p, 'K1-correction-closed');
  await go(p, 'gate'); await p.click('[data-gplan]'); await p.waitForTimeout(1500);
  s = await state();
  const bl = s.gate.plan.blockers.join(' | ');
  ok('K', 'after the correction only the environment lock blocks paid narration', s.gate.plan.blockers.length === 1 && bl.includes('disabled in this environment'), bl);
  await go(p, 'gate'); await shot(p, 'K2-gate-after-correction');
  const { execFileSync } = await import('node:child_process');
  const frame = (r, n) => { const f = `var/dashboard-uat/studio/${PID}/${r.file}`; execFileSync('ffmpeg', ['-v', 'error', '-y', '-ss', '0.4', '-i', f, '-frames:v', '1', '-vf', 'scale=540:-2', `${SH}/${n}.png`]); return fs.readFileSync(`${SH}/${n}.png`); };
  const b1 = frame(before, 'K3-hook-before'), b2 = frame(after, 'K4-hook-after');
  ok('K', 'frame 1 of the hook before and after the correction saved and different', !b1.equals(b2), `${SH}/K3-hook-before.png vs K4-hook-after.png`);
  fs.writeFileSync(`${out}/K-renders.json`, JSON.stringify({ before, after }, null, 1));
  { const w = await allFit(p); ok('K', 'still no sideways scroll on any screen after the owner\'s notes and decisions', w.length === 0, w.join(',') || 'all fit'); }
  await p.close();
}
async function L() {   // fix found in Claude's own frame review: banners carried over + stamp overlap → re-render → clean re-review
  let s = await state();
  const before = s.renders.filter((r) => r.state === 'ok').pop();
  const fixed = JSON.parse(JSON.stringify(BRIEF));
  const lines = [{ text: 'يقولون:', size: 64, at: 0.0, in: 'slam' }, { text: 'أول ساعة', size: 92, at: 0.1, in: 'slam' }, { text: 'مقاومة للماء؟', size: 92, at: 0.3, in: 'slam' }];
  fixed.scenes.h.concepts.kinetic_type = { ...fixed.scenes.h.concepts.kinetic_type, lines, y: 380, stamp: { text: 'ليس تمامًا', at: 1.2, y: 860 } };
  fixed.hook_visuals.H1.params = { ...fixed.hook_visuals.H1.params, lines, y: 380, stamp: { text: 'ليس تمامًا', at: 1.2, y: 860 } };
  await post('art_brief', { brief: fixed }, 'art:claude');
  const p = await page('phone');
  await go(p, 'storyboard'); await p.click('[data-build]'); await p.waitForTimeout(1200);
  await go(p, 'draft'); await p.click('#renderBtn'); await p.waitForTimeout(3000);
  await untilIdle('render r3', 2400);
  s = await state();
  const after = s.renders.filter((x) => x.state === 'ok').pop();
  ok('L', 'clean draft rendered after the banner/stamp fix', after.id !== before.id, `${before.id} → ${after.id}`);
  await go(p, 'draft');
  await p.click('h2').catch(() => p.click('body')); await p.evaluate(() => { const v = document.querySelector('video[data-film]'); v.muted = false; v.volume = 1; v.playbackRate = 2; return v.play(); });   // audible, as an owner watches it
  await p.waitForTimeout((after.seconds / 2) * 1000 + 3000);
  await p.click(`[data-rdec="approved_as_draft"][data-r="${after.id}"]`); await p.waitForTimeout(700);
  await go(p, 'review'); await p.click('[data-run="run_review"]'); await p.waitForTimeout(1500); await untilIdle('review r3', 1200);
  s = await state();
  const last = s.review.runs[s.review.runs.length - 1];
  const fs3 = Object.values(s.review.findings).filter((f) => f.run === last.id);
  ok('L', 're-review of the clean draft: no carried-over banner, no text overlap, no unsupported claim', !fs3.some((f) => ['BANNER_CARRIED_OVER', 'TEXT_OVERLAP', 'CLAIM_ON_SCREEN'].includes(f.code)), fs3.map((f) => `${f.code}@${f.scene}`).join(',') || 'no findings');
  await go(p, 'review');
  for (const f of fs3) { await p.fill(`[data-fnote="${f.id}"]`, 'checked on the clean draft'); await p.click(`[data-fdec="dismissed"][data-f="${f.id}"]`); await p.waitForTimeout(500); }
  await go(p, 'gate'); await p.click('[data-gplan]'); await p.waitForTimeout(1500); await go(p, 'gate'); await shot(p, 'L1-gate-final');
  await go(p, 'overview'); await shot(p, 'L2-overview-final');
  const { execFileSync } = await import('node:child_process');
  execFileSync('ffmpeg', ['-v', 'error', '-y', '-sseof', '-3', '-i', `var/dashboard-uat/studio/${PID}/${after.file}`, '-frames:v', '1', '-vf', 'scale=540:-2', `${SH}/L3-endcard-after.png`]);
  execFileSync('ffmpeg', ['-v', 'error', '-y', '-sseof', '-3', '-i', `var/dashboard-uat/studio/${PID}/${before.file}`, '-frames:v', '1', '-vf', 'scale=540:-2', `${SH}/L3-endcard-before.png`]);
  await p.close();
}
async function D3() {   // the script changes after voicing: the old take must not count (audit D-01)
  const p = await page('phone');
  await go(p, 'hook'); await p.click('[data-hsel="H2"]'); await p.waitForTimeout(900);
  let s = await state(); const v6 = s.scripts.slice(-1)[0].v;
  await go(p, `script/${v6}`); await p.click('#approveScript'); await p.waitForTimeout(800);
  s = await state();
  ok('R', 'after switching the hook, the old hook take is stale and Draft voice is no longer Done', s.voice.lines.h.status === 'stale' && s.steps.find((x) => x.id === 'voice').state !== 'approved', JSON.stringify(s.voice.lines.h));
  await go(p, 'voice'); await shot(p, 'D10-stale-line');
  ok('R', 'the voice screen says the take is for older text and offers to record the changed line', !!(await p.$('[data-stale="h"]')) && (await p.textContent('#makeVoice')).includes('1 line'));
  await go(p, 'inbox'); ok('R', 'the inbox asks to re-record h', (await p.textContent('main')).includes('Re-record h'));
  await go(p, 'voice'); await p.click('#makeVoice'); await p.waitForTimeout(1500); await untilIdle('re-record h', 600);
  s = await state();
  ok('R', 'only the changed line was recorded again', s.voice.lines.h.status === 'candidate' && Object.values(s.voice.by_line).reduce((n, v) => n + v.length, 0) === 15, `${Object.values(s.voice.by_line).reduce((n, v) => n + v.length, 0)} takes`);
  // back to H1: the original H1 take matches the text again and counts again
  await go(p, 'hook'); await p.click('[data-hsel="H1"]'); await p.waitForTimeout(900);
  s = await state(); const v7 = s.scripts.slice(-1)[0].v;
  await go(p, `script/${v7}`); await p.click('#approveScript'); await p.waitForTimeout(800);
  await go(p, 'hook'); await p.check('#payofflines input[value="l13"]'); await p.click('[data-deliver="delivered"]'); await p.waitForTimeout(700);
  s = await state();
  ok('R', 'back on H1 the approved H1 take counts again; hook delivered again', s.voice.lines.h.status === 'approved' && s.hooks.delivery?.decision === 'delivered', JSON.stringify(s.voice.lines.h));
  await p.close();
}
async function D4() {   // seeking is not listening (audit D-04). Run on a DISPOSABLE copy (tools/uat_d4_copy.sh): it switches the hook.
  const p = await page('phone'); let s = await state();
  if (s.voice.lines.h.status !== 'candidate') {          // make the re-recorded H2 hook take the current candidate again
    await go(p, 'hook'); await p.click('[data-hsel="H2"]'); await p.waitForTimeout(900);
    s = await state(); const v = s.scripts.slice(-1)[0].v;
    await go(p, `script/${v}`); await p.click('#approveScript'); await p.waitForTimeout(800); s = await state();
  }
  const ln = s.voice.lines.h; const tid = ln.take;
  ok('R', 'disposable copy: the H2 hook take is a candidate waiting for a decision', ln.status === 'candidate', JSON.stringify(ln));
  await go(p, 'voice/h');
  // the same opening quarter four times is not hearing the take (audit round 2)
  const sec = s.voice.takes[tid].seconds;
  for (let k = 0; k < 4; k++) { await p.click(`[data-tplay="${tid}"]`); await p.waitForTimeout(sec * 250); await p.evaluate(() => document.querySelectorAll('audio').forEach((a) => a.pause())); await p.waitForTimeout(300); }
  await p.click(`[data-tdec="rejected"][data-t="${tid}"]`); await p.waitForTimeout(600);
  let t0 = await p.textContent('#toast');
  ok('R', 'replaying the opening quarter four times does not count as hearing the take; decision refused', t0.includes('does not count') && (await state()).voice.takes[tid].status === 'candidate', t0);
  await go(p, 'voice/h');
  const svg = p.locator(`[data-wave="${tid}"]`); const box = await svg.boundingBox();
  await p.mouse.click(box.x + box.width * 0.97, box.y + box.height / 2); await p.waitForTimeout(1500);
  await p.click(`[data-tdec="rejected"][data-t="${tid}"]`); await p.waitForTimeout(600);
  let t = await p.textContent('#toast'); s = await state();
  ok('R', 'clicking the waveform near the end does not count as listening; the decision is refused', t.includes('does not count') && s.voice.takes[tid].status === 'candidate', t);
  await shot(p, 'D11-seek-refused');
  await p.click(`[data-tplay="${tid}"]`); await p.waitForTimeout(s.voice.takes[tid].seconds * 1000 + 1500);
  const heard = await p.textContent(`[data-heard="${tid}"]`);
  await p.click(`[data-tdec="rejected"][data-t="${tid}"]`); await p.waitForTimeout(800);
  t = await p.textContent('#toast'); s = await state();
  ok('R', 'after playing the take through, the same decision is accepted', s.voice.takes[tid].status === 'rejected', `${heard} · ${t}`);
  await p.close();
}
async function F2() {   // a free-text art request goes to the operator; nothing pretends to be a revision (audit D-05)
  const p = await page('phone');
  await go(p, 'art'); await p.click('[data-amod="l11-kinetic_type"]'); await p.waitForTimeout(300);
  await p.fill('#mnote', 'make the second line say the watch kept time, and add the date'); await p.click('[data-msave="l11-kinetic_type"]'); await p.waitForTimeout(900);
  let s = await state();
  ok('F', 'a note-only change request waits for the art operator and makes no fake version', s.art.requests.slice(-1)[0].status === 'waiting_operator' && s.art.concepts['l11-kinetic_type'].versions.length === 1);
  await go(p, 'art'); await shot(p, 'F5-note-waiting-operator');
  const c = s.art.concepts['l11-kinetic_type'];
  const params = { ...c.params, lines: [{ text: 'بعد عشر ساعات', size: 70 }, { text: 'ما تزال تعمل', size: 96, at: 0.7 }, { text: '21 أكتوبر 1927', size: 44, at: 1.4 }] };
  const r = await post('art_operator_revision', { concept: 'l11-kinetic_type', params, note: 'second line and the date, as asked' }, 'art:claude');
  ok('F', 'the art operator answers with new parameters (recorded as operator input)', r.status === 'recorded');
  await untilIdle('operator revision', 600);
  s = await state(); const vs = s.art.concepts['l11-kinetic_type'].versions;
  ok('F', 'the operator\'s revision is a real new image (v2 differs from v1)', vs.length === 2 && vs[1].stills[0] !== vs[0].stills[0] && !vs[1].no_visible_change);
  // a structured change WITH a note: the change is drawn, and the note still goes to the art operator (audit N-3)
  await go(p, 'art'); await p.click('[data-amod="l2-kinetic_type"]'); await p.waitForTimeout(300);
  await p.click('[data-mod="theme:tk-ink"]'); await p.fill('#mnote', 'and put the year 1926 on its own line'); await p.click('[data-msave="l2-kinetic_type"]'); await p.waitForTimeout(900);
  await untilIdle('revision with a note', 600);
  s = await state(); const rq = s.art.requests.filter((q) => q.concept === 'l2-kinetic_type').pop();
  ok('F', 'a change plus a note: the change makes v2 and the note waits for the art operator (not marked done)', s.art.concepts['l2-kinetic_type'].versions.length === 2 && rq.status === 'waiting_operator', JSON.stringify({ status: rq.status, version: rq.version }));
  // a change the drawing would ignore is not offered
  await go(p, 'art'); await p.click('[data-amod="l2-animated_timeline"]'); await p.waitForTimeout(300);
  ok('F', 'changes a drawing would ignore are not offered (timeline: no "Bigger text")', (await p.locator('#mods [data-mod="text_size:1.2"]').count()) === 0 && (await p.textContent('.sheet, #sheet, body')).includes('Not offered'));
  await p.click('[data-close]').catch(() => {}); await p.waitForTimeout(300);
  // revise APPROVED art: the approved version stays in the film until the new one is approved, which then replaces it
  const ap0 = s.art.approved.l9;
  await go(p, 'art'); await p.click('[data-amod="l9-map"]'); await p.waitForTimeout(300);
  await p.click('[data-mod="text_size:1.2"]'); await p.click('[data-msave="l9-map"]'); await p.waitForTimeout(900);
  await untilIdle('revision of approved l9', 600);
  s = await state(); const nv = s.art.concepts['l9-map'].versions.slice(-1)[0].v; const vsm = s.art.concepts['l9-map'].versions;
  ok('F', 'the revision of the approved map looks different from every earlier version', !vsm.slice(-1)[0].no_visible_change && vsm.slice(0, -1).every((x) => x.stills[0] !== vsm.slice(-1)[0].stills[0]));
  await go(p, 'inbox'); ok('F', 'the inbox asks to approve or reject the new version of the approved art', (await p.textContent('main')).includes(`approve or reject v${nv}`));
  ok('F', 'changes can be requested on approved art; the approved version stays in use meanwhile', nv === ap0.version + 1 && s.art.approved.l9.version === ap0.version, `v${nv}, approved v${s.art.approved.l9.version}`);
  await go(p, 'art'); await p.locator('[data-scene="l9"]').scrollIntoViewIfNeeded(); await shot(p, 'F6-approved-art-revision');
  await p.click(`[data-aok="l9-map"][data-av="${nv}"]`); await p.waitForTimeout(800);
  s = await state(); const old = s.art.concepts['l9-map'].versions.find((x) => x.v === ap0.version);
  ok('F', 'approving the new version replaces the old approval in one step; the old one is kept as replaced', s.art.approved.l9.version === nv && old.status === 'replaced', `approved v${s.art.approved.l9.version}, v${ap0.version} ${old.status}`);
  await p.close();
}
async function Z() {   // the finished project: rebuild the plan; nothing but the workspace lock may block paid narration
  const p = await page('phone');
  await go(p, 'gate'); await p.click('[data-gplan]'); await p.waitForTimeout(1500);
  const s = await state(); const bl = s.gate.plan.blockers;
  ok('Z', 'finished project: the rebuilt plan is blocked only by the workspace lock (no paid call possible here)', bl.length === 1 && bl[0].includes('disabled in this environment'), bl.join(' | '));
  const acc = s.history.filter((h) => ['gate_authorize', 'final_generate'].includes(h.action));
  ok('Z', 'finished project: no paid authorization or generation was ever accepted; every attempt is in the refusal log', acc.length === 0 && s.gate.attempts.length >= 3, `${acc.length} accepted · ${s.gate.attempts.length} refused attempts`);
  await go(p, 'gate'); await shot(p, 'Z1-gate-finished');
  await p.close();
}
const PH = { A, B, C: C_, D, D2, D3, D4, DW, E, F2, G, H, H2, I, J, K, L, R, Z };
for (const ph of phases) { console.log('== phase', ph); try { await PH[ph](); } catch (e) { ok(ph, 'phase crashed', false, e.stack); } }
ok('page', 'no JavaScript errors on the pages', errors.length === 0, errors.slice(0, 5).join(' | '));
await b.close();
