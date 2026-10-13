// End-to-end decision sync: Artifact page → page database → export → local ingestion → event log → receipts → page.
//   VD_DASHBOARD_VAR=<copy of var/dashboard> node tools/sync_e2e_test.mjs OUT_DIR
// The page is the real static Artifact build (mode 'artifact'). The Artifact database is replaced by an in-browser
// mock with the same calls the page uses (claude.use('db') → doc(path).set, collection(path).onSnapshot), persisted in
// localStorage so a reload behaves like the hosted store. Everything on the local side is the real code (sync.ingest).
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
const require = createRequire(import.meta.url);
const { chromium, devices } = require(process.env.PW_MODULE || '/opt/node22/lib/node_modules/playwright');
const [out] = process.argv.slice(2);
const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
if (!process.env.VD_DASHBOARD_VAR || process.env.VD_DASHBOARD_VAR.endsWith('var/dashboard')) throw new Error('point VD_DASHBOARD_VAR at a copy');
const py = (...a) => execFileSync('python3', ['tools/sync_helper.py', ...a], { cwd: ROOT, env: { ...process.env, PYTHONPATH: ROOT, ELEVENLABS_API_KEY: '', FAL_KEY: '', VIDEO_DIRECTOR_PAID_ENABLED: '0' } }).toString().trim().split('\n').pop();
const res = []; const ok = (n, c, d = '') => { res.push({ name: n, pass: !!c, detail: String(d) }); };
fs.mkdirSync(out, { recursive: true });

// 1. the static Artifact copy, from the test log
const site = path.join(out, 'site'); fs.rmSync(site, { recursive: true, force: true }); fs.mkdirSync(site, { recursive: true });
py('build', site);
const html = fs.readFileSync(path.join(site, 'index.html'), 'utf8');
ok('built page is the Artifact mode', html.includes("'artifact'") || html.includes('"artifact"'));

// static server with byte ranges (like the Artifact host is expected to provide; unverified there, see report)
const TYPES = { '.html': 'text/html; charset=utf-8', '.mp4': 'video/mp4', '.webm': 'video/webm', '.m4a': 'audio/mp4', '.mp3': 'audio/mpeg', '.jpg': 'image/jpeg', '.png': 'image/png', '.json': 'application/json', '.wav': 'audio/wav', '.ogg': 'audio/ogg', '.opus': 'audio/ogg' };
const srv = http.createServer((q, r) => {
  const rel = decodeURIComponent(q.url.split('?')[0]); const f = path.join(site, rel === '/' ? 'index.html' : rel);
  if (!f.startsWith(site) || !fs.existsSync(f) || !fs.statSync(f).isFile()) { r.writeHead(404); return r.end(); }
  const n = fs.statSync(f).size, t = TYPES[path.extname(f)] || 'application/octet-stream', m = /bytes=(\d*)-(\d*)/.exec(q.headers.range || '');
  if (rel === '/' || rel === '/index.html') {   // the Artifact host wraps the page in this skeleton (doctype + phone viewport)
    const page = fs.readFileSync(f, 'utf8');
    const doc = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><style>body{margin:0}</style></head><body>' + page + '</body></html>';
    r.writeHead(200, { 'Content-Type': TYPES['.html'] }); return r.end(doc);
  }
  if (!m) { r.writeHead(200, { 'Content-Type': t, 'Content-Length': n, 'Accept-Ranges': 'bytes' }); return fs.createReadStream(f).pipe(r); }
  const s = m[1] ? +m[1] : n - +m[2], e = m[1] && m[2] ? Math.min(+m[2], n - 1) : n - 1;
  r.writeHead(206, { 'Content-Type': t, 'Content-Length': e - s + 1, 'Content-Range': `bytes ${s}-${e}/${n}`, 'Accept-Ranges': 'bytes' });
  fs.createReadStream(f, { start: s, end: e }).pipe(r);
}).listen(0); await new Promise((r) => srv.on('listening', r));
const base = `http://127.0.0.1:${srv.address().port}`;

const MOCK = () => {
  const K = '__mockdb', load = () => { try { return JSON.parse(localStorage.getItem(K)) || { decisions: {}, sync: {} }; } catch (e) { return { decisions: {}, sync: {} }; } };
  const L = { decisions: [], sync: [] }, save = (s) => localStorage.setItem(K, JSON.stringify(s));
  const snap = (c) => ({ docs: Object.entries(load()[c]).map(([id, v]) => ({ id, data: () => v })) });
  window.__mockEmit = (c) => L[c].forEach((f) => f(snap(c)));
  window.__mockStore = () => load();
  window.__mockPut = (c, id, v) => { const s = load(); s[c][id] = v; save(s); window.__mockEmit(c); };
  const db = Object.freeze({
    doc(p) { const [c, id] = p.split('/'); return { async set(v) { const s = load(); s[c][id] = JSON.parse(JSON.stringify(v)); save(s); setTimeout(() => window.__mockEmit(c)); } }; },
    collection(c) { return { onSnapshot(fn) { L[c].push(fn); setTimeout(() => fn(snap(c))); return () => {}; } }; },
  });
  window.claude = Object.freeze({ use: async (n) => (n === 'db' ? db : null) });
};
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args: ['--no-proxy-server', '--autoplay-policy=no-user-gesture-required'] });
const iphone = { ...devices['iPhone 13'] }; delete iphone.defaultBrowserType;
const ctx = await b.newContext({ ...iphone, colorScheme: 'light' });
await ctx.addInitScript(MOCK);
await ctx.route(/fonts\.(googleapis|gstatic)/, (r) => r.abort());
const p = await ctx.newPage(); const errors = []; p.on('pageerror', (e) => errors.push(e.message));
const go = async (h) => { await p.goto(base + '/#' + h); await p.waitForTimeout(700); };
const syncText = (item) => p.evaluate((it) => { const btn = document.querySelector(`button[data-item="${it}"]`); const s = btn && btn.closest('.acts').querySelector('.sync'); return s ? s.textContent : null; }, item);
const click = async (item, dec) => { await p.locator(`button[data-item="${item}"][data-dec="${dec}"]`).first().scrollIntoViewIfNeeded(); await p.locator(`button[data-item="${item}"][data-dec="${dec}"]`).first().click(); await p.waitForTimeout(400); };

const I = { concept: 'concept-ep7-b3-scientific_diagram', version: 'ep7-b1-b1_v3', locked: 'ep7-b2-final', finding: 'f_70dc55998b', check: 'voice-p2-q-tk-quartz-107', refused: 'voice-p2-1-tk-steel-59' };

// 2. decisions on the page (real buttons)
await go('dh~art~b3'); await click(I.concept, 'concept_selected');
ok('page: concept selection shows as pending, not recorded', /waiting for the local app/.test(await syncText(I.concept)), await syncText(I.concept));
await go('dh~art~b1'); await p.locator('button[data-arttab="revisions"]').click(); await p.waitForTimeout(300);
await click(I.version, 'approved');
await go('dh~art~b2'); await p.locator('button[data-arttab="revisions"]').click(); await p.waitForTimeout(300);
await click(I.locked, 'rejected');                                   // the local app will approve this first → conflict (locked)
await go('dh~reviews'); await click(I.finding, 'accepted');            // the local app will decide later → conflict (older)
await go('tk~reviews');
const card = p.locator(`.check[data-check="${I.check}"]`); await card.scrollIntoViewIfNeeded();
ok('page: listening answer blocked before playing', await card.locator('button[data-dec="article_heard"]').isDisabled());
await card.locator('button[data-word]').click();
await p.waitForFunction((id) => { const a = document.querySelector(`audio[data-audio="${id}"]`); return a && a.played.length && a.paused; }, I.check, { timeout: 15000 });
await p.waitForTimeout(300); await click(I.check, 'unsure');
await go('tk~reviews');
const pendingHeader = await p.locator('main').textContent();
ok('page: reviews header counts decisions waiting for the local app', /5 decision\(s\) saved here, waiting for the local app/.test(pendingHeader));
await shot('sync-1-pending');

// a reload keeps them (they live in the page database, not in memory)
await p.reload(); await p.waitForTimeout(800); await go('dh~art~b3');
ok('page: after reload the decision is still pending', /waiting for the local app/.test(await syncText(I.concept)));

// injected rows: what another device or an old page version could write
const now = Date.now();
await p.evaluate(([I, now]) => {
  const st = window.__mockStore().decisions; const c = Object.values(st).find((d) => d.item === I.concept);
  window.__mockPut('decisions', 'second-device-1', { decision_id: 'second-device-1', item: I.concept, decision: 'concept_selected', note: '', at: new Date(now + 5000).toISOString() });
  window.__mockPut('decisions', 'old-page-1', { decision_id: 'old-page-1', item: I.refused, decision: 'article_heard', note: '', at: new Date(now).toISOString() });
  window.__mockPut('decisions', 'unknown-item-1', { decision_id: 'unknown-item-1', item: 'ep9-zz-v1', decision: 'approved', note: '', at: new Date(now).toISOString() });
}, [I, now]);

// 3. meanwhile, in the local app
const locA = JSON.parse(py('local', I.locked, 'approved'));
await new Promise((r) => setTimeout(r, 1100));
const locB = JSON.parse(py('local', I.finding, 'dismissed'));
ok('local app: decisions recorded directly', locA.status === 'recorded' && locB.status === 'recorded', JSON.stringify([locA, locB]));

// 4. EXPORT (the folder format ArtifactData list writes) + one unreadable file
const exp = path.join(out, 'export'); fs.rmSync(exp, { recursive: true, force: true }); fs.mkdirSync(path.join(exp, 'decisions'), { recursive: true });
const store = await p.evaluate(() => window.__mockStore());
for (const [id, v] of Object.entries(store.decisions)) fs.writeFileSync(path.join(exp, 'decisions', id + '.json'), JSON.stringify({ id, data: v }));
fs.writeFileSync(path.join(exp, 'decisions', 'corrupt-1.json'), '{"decision_id": "corrupt-1", "item": ');
const before = JSON.parse(py('events'));

// 5. INGEST
const r1 = JSON.parse(py('ingest', exp, path.join(out, 'receipts1.json')));
const by = Object.fromEntries(r1.receipts.map((r) => [r.decision_id, r]));
const pageId = (item) => Object.values(store.decisions).find((d) => d.item === item && !['second-device-1', 'old-page-1', 'unknown-item-1'].includes(d.decision_id)).decision_id;
ok('ingest: concept selection recorded', by[pageId(I.concept)].status === 'recorded');
ok('ingest: version approval recorded', by[pageId(I.version)].status === 'recorded');
ok('ingest: listening answer with playback proof recorded', by[pageId(I.check)].status === 'recorded');
ok('ingest: same decision from a second device is a duplicate', by['second-device-1'].status === 'duplicate', by['second-device-1'].reason);
ok('ingest: page decision on an item the local app approved → conflict (locked)', by[pageId(I.locked)].status === 'conflict', by[pageId(I.locked)].reason);
ok('ingest: older page decision than a newer local one → conflict', by[pageId(I.finding)].status === 'conflict', by[pageId(I.finding)].reason);
ok('ingest: listening answer without playback proof → refused', by['old-page-1'].status === 'refused', by['old-page-1'].reason);
ok('ingest: unknown item → failed', by['unknown-item-1'].status === 'failed', by['unknown-item-1'].reason);
ok('ingest: unreadable export file → failed (reported, not skipped)', by['corrupt-1'] && by['corrupt-1'].status === 'failed', by['corrupt-1'] && by['corrupt-1'].reason);
ok('ingest: every decision has exactly one outcome', r1.receipts.length === Object.keys(store.decisions).length + 1, JSON.stringify(r1.summary));
const after1 = JSON.parse(py('events'));
const newRows = after1.slice(before.length);
ok('event log: 3 decisions added, each with origin artifact', newRows.filter((e) => e.kind === 'review_decided').length === 3 && newRows.filter((e) => e.kind === 'review_decided').every((e) => e.origin === 'artifact'));
ok('event log: every non-recorded outcome logged as a sync event', newRows.filter((e) => e.kind === 'sync').length === 6, JSON.stringify(newRows.filter((e) => e.kind === 'sync').map((e) => e.status)));

// 6. receipts back to the page
await go('dh~art~b3');
ok('page: before receipts arrive, nothing claims to be recorded', /waiting for the local app/.test(await syncText(I.concept)));
for (const w of JSON.parse(fs.readFileSync(path.join(out, 'receipts1.json'), 'utf8'))) await p.evaluate(([c, id, v]) => window.__mockPut(c, id, v), [w.collection, w.doc_id, w.data]);
await p.waitForTimeout(500);
const tConcept = await syncText(I.concept);
await p.locator(`button[data-item="${I.concept}"]`).first().scrollIntoViewIfNeeded();
ok('page: after the receipt the concept shows recorded with its event number', new RegExp('Recorded in the event log · #' + by[pageId(I.concept)].event).test(tConcept), tConcept);
await shot('sync-2-recorded-concept');
await go('dh~art~b1'); await p.locator('button[data-arttab="revisions"]').click(); await p.waitForTimeout(300);
const tVer = await syncText(I.version);
ok('page: approved version shows recorded and locked', /Locked/.test(tVer) && /Recorded/.test(tVer), tVer);
await go('dh~art~b2'); await p.locator('button[data-arttab="revisions"]').click(); await p.waitForTimeout(300);
const tLock = await syncText(I.locked); await p.locator(`button[data-item="${I.locked}"]`).first().scrollIntoViewIfNeeded();
ok('page: conflicting decision says it was not recorded and why', /not recorded/i.test(tLock) && /locked/.test(tLock), tLock);
await shot('sync-3-conflict');
await go('tk~reviews');
const tHead = await p.locator('main').textContent();
ok('page: header now reports problems instead of pending', /not recorded: see below/.test(tHead));
ok('page: each decision that was not recorded is listed with its reason', ['ep9-zz-v1', I.refused, I.locked, I.finding].every((x) => tHead.includes(x)) && /not a confirmed listening result/.test(tHead));
await shot('sync-4-reviews-after');

// 7. idempotency: the same export again
const r2 = JSON.parse(py('ingest', exp, path.join(out, 'receipts2.json')));
const after2 = JSON.parse(py('events'));
ok('re-ingest: nothing new recorded', r2.summary.recorded === 0, JSON.stringify(r2.summary));
ok('re-ingest: recorded decisions come back as duplicate with the same event number', ['concept', 'version', 'check'].every((k) => { const a = r2.receipts.find((r) => r.decision_id === pageId(I[k])); return a.status === 'duplicate' && a.event === by[pageId(I[k])].event; }));
ok('re-ingest: no new decision events and no repeated sync events', after2.filter((e) => e.kind === 'review_decided').length === after1.filter((e) => e.kind === 'review_decided').length && after2.length === after1.length, `${after1.length} → ${after2.length}`);
ok('no page errors', errors.length === 0, errors.join(' | '));

async function shot(n) { await p.screenshot({ path: `${out}/${n}.png` }); }
await b.close(); srv.close();
fs.writeFileSync(`${out}/sync-results.json`, JSON.stringify({ results: res, ingest1: r1, ingest2: r2.summary }, null, 1));
for (const r of res) console.log((r.pass ? 'PASS ' : 'FAIL ') + r.name + (r.pass ? '' : '  ← ' + r.detail));
console.log(`${res.filter((r) => r.pass).length}/${res.length} passed`);
process.exit(res.every((r) => r.pass) ? 0 : 1);
