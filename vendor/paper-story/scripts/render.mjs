#!/usr/bin/env node
/**
 * paper-story renderer.
 *
 *   node render.mjs <storyboard.json> -o out.mp4 [--scale 1.5] [--audio vo.mp3] [--music bed.mp3]
 *   node render.mjs <storyboard.json> --still 2.5,9 -o stills/       one PNG per time (fast QA)
 *   node render.mjs <storyboard.json> --textmap 0,0.5,1 -o dir        the words on screen and the frame without them (quality bar)
 *   node render.mjs <storyboard.json> --safe zones.json               words inside a platform's button zones (director/platforms.py)
 *   node render.mjs <storyboard.json> --check                        lists every face a banner, card or picture covers,
 *                                                                     and every bubble or word hidden under the banner
 *   node render.mjs <storyboard.json> --sheet [--every 2] -o sheet.png   contact sheet of the whole video
 *
 * Options: --fps N  --scale N (1 = 720x1280, 1.5 = 1080x1920)  --workers N  --from S --to S
 *          --crf N  --keep-frames  --voice-gain dB  --music-gain dB (default -6)  --no-duck (music stays level under the voice)
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';
import { execFileSync, spawnSync } from 'node:child_process';
import crypto from 'node:crypto';

const here = path.dirname(fileURLToPath(import.meta.url));
const stageUrl = pathToFileURL(path.join(here, '..', 'engine', 'stage.html')).href;

// ---------------------------------------------------------------- args
const argv = process.argv.slice(2);
const opt = { workers: Math.max(1, Math.min(4, os.cpus().length - 1)), scale: 1, crf: 18, every: 2 };
let sbPath = null;
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  const next = () => argv[++i];
  if (a === '-o' || a === '--out') opt.out = next();
  else if (a === '--scale') opt.scale = +next();
  else if (a === '--fps') opt.fps = +next();
  else if (a === '--workers') opt.workers = +next();
  else if (a === '--audio') opt.audio = next();
  else if (a === '--music') opt.music = next();
  else if (a === '--from') opt.from = +next();
  else if (a === '--to') opt.to = +next();
  else if (a === '--crf') opt.crf = +next();
  else if (a === '--chunk') opt.chunk = +next();
  else if (a === '--every') opt.every = +next();
  else if (a === '--still') opt.still = next().split(',').map(Number);
  else if (a === '--sheet') opt.sheet = true;
  else if (a === '--check') opt.check = true;
  else if (a === '--safe') opt.safe = next();
  else if (a === '--textmap') opt.textmap = next().split(',').map(Number);
  else if (a === '--keep-frames') opt.keep = true;
  else if (a === '--review') opt.review = true;
  else if (a === '--final') opt.final = true;
  else if (a === '--voice-gain') opt.voiceGain = +next();
  else if (a === '--music-gain') opt.musicGain = +next();
  else if (a === '--no-duck') opt.noDuck = true;
  else if (!sbPath) sbPath = a;
  else die('Unexpected argument: ' + a);
}
function die(m) { console.error('render: ' + m); process.exit(1); }
if (!sbPath) die('usage: node render.mjs <storyboard.json> -o out.mp4 [options]   (see header of this file)');
sbPath = path.resolve(sbPath);
const sbDir = path.dirname(sbPath);
const sb = JSON.parse(fs.readFileSync(sbPath, 'utf8'));
const resolveFile = (p) => (/^(https?:|data:|file:)/.test(p) ? p : pathToFileURL(path.resolve(sbDir, p)).href);
// ---- asset resolution -------------------------------------------------------
// 1. Relative paths in "src", "avatar" and puppet "parts" resolve against the storyboard folder.
// 2. An element with "asset": "ep1_boulder_01" and no src picks up <storyboard folder>/assets/ep1_boulder_01.(jpg|png|webp)
//    when that file exists, so real evidence replaces a placeholder just by being dropped into assets/.
// 3. A puppet with "character": "ali" picks up assets/characters/ali/<front|side>/<part>.png for every part found.
const placeholders = [];
const PARTS = ['head', 'torso', 'armU', 'armL', 'hand', 'legU', 'legL', 'foot'];
const findAsset = (id) => { for (const e of ['jpg', 'jpeg', 'png', 'webp']) { const f = path.join(sbDir, 'assets', id + '.' + e); if (fs.existsSync(f)) return f; } return null; };
(function fix(o) {
  if (Array.isArray(o)) o.forEach(fix);
  else if (o && typeof o === 'object') {
    for (const k of Object.keys(o)) {
      if ((k === 'src' || k === 'avatar') && typeof o[k] === 'string') o[k] = resolveFile(o[k]);
      else if (k === 'parts' && o[k] && typeof o[k] === 'object') for (const pk of Object.keys(o[k])) o[k][pk] = resolveFile(o[k][pk]);
      else fix(o[k]);
    }
    if (typeof o.asset === 'string' && !o.src && ['photo', 'igpost', 'image', 'phone', 'door', 'laptop', 'cutout', 'reveal'].includes(o.type)) {
      const f = findAsset(o.asset);
      if (f) o.src = pathToFileURL(f).href; else placeholders.push(o.asset);
    }
    if (o.type === 'puppet' && typeof o.character === 'string') {
      const dir = path.join(sbDir, 'assets', 'characters', o.character, o.view === 'side' ? 'side' : 'front');
      const found = {};
      for (const pn of PARTS) { const f = path.join(dir, pn + '.png'); if (fs.existsSync(f)) found[pn] = pathToFileURL(f).href; }
      if (Object.keys(found).length) o.parts = Object.assign(found, o.parts || {});
      else placeholders.push('character:' + o.character + (o.view === 'side' ? ' (side)' : ''));
    }
  }
})(sb);
if (opt.review) sb.review = true;
const fps = opt.fps || sb.fps || 30;
sb.fps = fps;
const abs = (p) => (p ? path.resolve(sbDir, p) : p);
const audio = opt.audio ? path.resolve(opt.audio) : abs(sb.audio && (sb.audio.voice || sb.audio.voiceover));
const music = opt.music ? path.resolve(opt.music) : abs(sb.audio && sb.audio.music);

// ---------------------------------------------------------------- tools
function findFfmpeg() {
  if (process.env.FFMPEG && fs.existsSync(process.env.FFMPEG)) return process.env.FFMPEG;
  const w = spawnSync('ffmpeg', ['-version']);
  if (w.status === 0) return 'ffmpeg';
  const py = spawnSync('python3', ['-c', 'import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())']);
  if (py.status === 0) return py.stdout.toString().trim();
  die('ffmpeg not found. Install it (apt-get install ffmpeg) or: pip install imageio-ffmpeg');
}
function loadPlaywright() {
  const cache = path.join(os.homedir(), '.cache', 'paper-story');
  const roots = [here, process.cwd(), cache, ...(process.env.NODE_PATH || '').split(path.delimiter).filter(Boolean)];
  try { roots.push(execFileSync('npm', ['root', '-g']).toString().trim()); } catch {}
  for (const r of roots) {
    try { const req = createRequire(path.join(r, 'x.js')); return req('playwright-core'); } catch {}
    try { const req = createRequire(path.join(r, 'node_modules', 'x.js')); return req('playwright-core'); } catch {}
  }
  console.error('render: installing playwright-core into ' + cache + ' (one time)...');
  fs.mkdirSync(cache, { recursive: true });
  if (!fs.existsSync(path.join(cache, 'package.json'))) fs.writeFileSync(path.join(cache, 'package.json'), '{"name":"paper-story-cache","private":true}');
  const r = spawnSync('npm', ['install', '--silent', '--prefix', cache, 'playwright-core'], { stdio: 'inherit' });
  if (r.status !== 0) die('could not install playwright-core. Run: npm i --prefix ~/.cache/paper-story playwright-core');
  return createRequire(path.join(cache, 'node_modules', 'x.js'))('playwright-core');
}
function chromiumPath() {
  const bases = [process.env.PLAYWRIGHT_BROWSERS_PATH, '/opt/pw-browsers', path.join(os.homedir(), '.cache', 'ms-playwright')].filter(Boolean);
  for (const b of bases) {
    if (!fs.existsSync(b)) continue;
    for (const d of fs.readdirSync(b).sort().reverse()) {
      for (const rel of ['chrome-linux/headless_shell', 'chrome-linux/chrome', 'chrome-linux64/chrome']) {
        const p = path.join(b, d, rel);
        if (d.startsWith('chromium') && fs.existsSync(p)) return p;
      }
    }
  }
  return undefined;
}

const ffmpeg = findFfmpeg();

// ---- video clips ------------------------------------------------------------
// A `video` element (vendor/studio-ext/clip.js) shows its clip as a JPG sequence extracted here once, at the clip's
// own frame rate: headless Chromium has no H.264 decoder and a <video> seek is not frame-accurate there. The frames are
// cached next to the storyboard by the clip's path, size and date, so the check, the stills and every worker share
// them; a worker never decodes video. No audio is ever taken from a clip.
const CLIP_MAX_H = 1920;
function clipFrames(src) {
  const file = src.startsWith('file:') ? fileURLToPath(src) : path.resolve(sbDir, src);
  if (!fs.existsSync(file)) { console.warn('video clip not found: ' + file); return null; }
  const st = fs.statSync(file);
  const key = crypto.createHash('sha1').update([file, st.size, Math.round(st.mtimeMs), CLIP_MAX_H].join('|')).digest('hex').slice(0, 16);
  let root = path.join(sbDir, '.clip-frames');
  try { fs.mkdirSync(root, { recursive: true }); fs.accessSync(root, fs.constants.W_OK); } catch { root = path.join(os.tmpdir(), 'pm-clip-frames'); fs.mkdirSync(root, { recursive: true }); }
  const dir = path.join(root, key), meta = path.join(dir, 'frames.json');
  if (!fs.existsSync(meta)) {
    const info = spawnSync(ffmpeg, ['-hide_banner', '-i', file], { encoding: 'utf8' }).stderr || '';
    const m = /Video:.*?(\d{2,5})x(\d{2,5}).*?([\d.]+) fps/.exec(info);
    const fps = m ? +m[3] : 24;
    const tmp = fs.mkdtempSync(path.join(root, key + '.part-'));
    const r = spawnSync(ffmpeg, ['-v', 'error', '-y', '-i', file, '-an', '-vf', `fps=${fps},scale=-2:'min(${CLIP_MAX_H},ih)'`, '-q:v', '2',
                                 path.join(tmp, 'f_%05d.jpg')], { stdio: 'inherit' });
    const n = fs.readdirSync(tmp).filter((f) => f.endsWith('.jpg')).length;
    if (r.status !== 0 || !n) { fs.rmSync(tmp, { recursive: true, force: true }); console.warn('could not read the frames of ' + file); return null; }
    fs.writeFileSync(path.join(tmp, 'frames.json'), JSON.stringify({ n, fps, w: m ? +m[1] : null, h: m ? +m[2] : null }));
    try { fs.renameSync(tmp, dir); } catch { fs.rmSync(tmp, { recursive: true, force: true }); }   // another render got there first
  }
  const fr = JSON.parse(fs.readFileSync(meta, 'utf8'));
  return { ...fr, base: pathToFileURL(path.join(dir, 'f_')).href };
}
for (const sc of sb.scenes || []) for (const e of sc.elements || []) if (e.type === 'video' && e.src && !e.frames) e.frames = clipFrames(e.src);
if (placeholders.length) {
  console.warn(`placeholders still showing (${placeholders.length}): ${[...new Set(placeholders)].join(', ')}`);
  if (opt.final) die('--final refused: real assets are missing for the placeholders above');
}
if (opt.final) {
  const bad = sb.scenes.filter((s) => !s.status);
  if (bad.length) die('--final refused: scenes without a truth status: ' + bad.map((s) => s.id || '?').join(', '));
}

function audioDuration(f) {
  const r = spawnSync(ffmpeg, ['-hide_banner', '-i', f], { encoding: 'utf8' });
  const m = /Duration: (\d+):(\d+):([\d.]+)/.exec(r.stderr || '');
  return m ? +m[1] * 3600 + +m[2] * 60 + +m[3] : null;
}
// Per-scene voice clips: scene.voice = "clip.wav". If dur is missing or "auto" the scene is as long as the clip + pad.
const voiceClips = [];
{
  let acc = 0;
  for (const sc of sb.scenes) {
    if (sc.voice) {
      const f = path.resolve(sbDir, sc.voice);
      if (!fs.existsSync(f)) die('scene voice not found: ' + f);
      const d = audioDuration(f);
      if (d == null) die('could not read the duration of ' + f);
      const at = sc.voiceAt != null ? sc.voiceAt : 0.15;
      if (sc.dur === undefined || sc.dur === 'auto') sc.dur = +Math.max(at + d + (sc.pad != null ? sc.pad : 0.45), sc.minDur || 0).toFixed(2);
      // captions follow the voice unless the storyboard pins them
      if (sc.captionStart == null) sc.captionStart = at + 0.05;
      if (sc.captionEnd == null) sc.captionEnd = Math.min(sc.dur - 0.2, at + d);
      else if (d > sc.dur) console.warn(`warning: voice clip ${sc.voice} is ${d.toFixed(1)}s but its scene is ${sc.dur}s`);
      voiceClips.push({ f, start: acc + (sc.voiceAt != null ? sc.voiceAt : 0.15) });
    } else if (sc.dur === undefined || sc.dur === 'auto') sc.dur = 4;
    acc += sc.dur;
  }
}
const pw = loadPlaywright();
const browser = await pw.chromium.launch({ executablePath: chromiumPath(), args: ['--no-sandbox', '--font-render-hinting=none', '--disable-gpu-vsync', '--allow-file-access-from-files'] }).catch((e) => die('could not launch Chromium: ' + e.message.split('\n')[0] + '\nTry: npx playwright-core install chromium'));

async function newPage() {
  const W = sb.width || 720, H = sb.height || 1280;
  const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: opt.scale });
  const page = await ctx.newPage();
  page.on('pageerror', (e) => { console.error('page error:', e.message); });
  page.on('console', (m) => { if (m.type() === 'error') console.error('page console:', m.text()); });
  await page.goto(stageUrl);
  const info = await page.evaluate((s) => window.PM.init(s), sb);
  // every picture decoded before the first screenshot (large cut-outs were still loading in the opening frames)
  await page.evaluate(() => Promise.all([...document.images].map((im) => (im.complete ? Promise.resolve() : new Promise((r) => { im.onload = im.onerror = r; }))
    .then(() => (im.decode ? im.decode().catch(() => {}) : null)))));
  return { page, info };
}
async function shot(page, t, file, png) {
  await page.evaluate((tt) => window.PM.setTime(tt), t);
  await page.evaluate(() => window.PM.settle && window.PM.settle());     // every clip frame asked for is decoded
  await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => r())));
  const take = () => page.screenshot(png ? { path: file, type: 'png' } : { path: file, type: 'jpeg', quality: 88 });
  // a frame Chromium could not capture (a busy or nearly full machine) is tried once more before the render fails
  try { await take(); } catch (e) {
    await new Promise((r) => setTimeout(r, 1500));
    try { await take(); } catch (e2) { e2.message = `frame at ${t.toFixed(2)} s: ` + e2.message; throw e2; }
  }
}

// ---------------------------------------------------------------- modes
const first = await newPage();
const duration = first.info.duration;
const outW = Math.round(first.info.width * opt.scale), outH = Math.round(first.info.height * opt.scale);

if (opt.check) {
  // every 0.2 s: is any face covered by a banner, caption card, bubble or picture? (elements marked "person": true)
  const hits = [];
  for (let t = 0.05; t < duration; t += 0.2) hits.push(...(await first.page.evaluate((tt) => window.PM.headClashes(tt), t)));
  const seen = new Map();
  for (const h of hits) { const k = h.scene + '|' + h.person + '|' + h.by; const e = seen.get(k); if (!e) seen.set(k, { ...h, from: h.t, to: h.t }); else { e.to = h.t; e.covered = Math.max(e.covered, h.covered); } }
  for (const e of seen.values()) console.log(`scene ${e.scene + 1}  ${e.from.toFixed(1)}-${e.to.toFixed(1)}s  ` + (e.under ? `${e.by} is ${e.covered}% under the banner` : `${e.by} covers ${e.covered}% of the head of ${e.person}`));
  console.log(seen.size ? seen.size + ' clash(es)' : 'no face covered, nothing under the banner');
  // layout: cut by the frame, prints over prints, things on the captions, pictures shown bigger than their file
  const lays = [];
  { const pg = await newPage(); for (let t = 0.05; t < duration; t += 0.2) lays.push(...(await pg.page.evaluate(([tt, k]) => window.PM.layout(tt, k), [t, opt.scale > 1 ? opt.scale : 1.5]))); }
  await browser.close();
  // runs of consecutive samples; a run shorter than 0.6 s is an entrance or exit (a drop, a slide), not a fault
  const runs = [], open = new Map();
  for (const h of lays) {
    const k = h.kind + '|' + h.scene + '|' + h.what, e = open.get(k);
    if (e && h.t - e.to < 0.25) { e.to = h.t; e.n++; e.pct = Math.max(e.pct, h.pct); } else { const r = { ...h, from: h.t, to: h.t, n: 1 }; runs.push(r); open.set(k, r); }
  }
  const SAY = { cut: (e) => `${e.what} is ${e.pct}% outside the frame`, overlap: (e) => `${e.what} (${e.pct}%)`,
                caption: (e) => `${e.what} sits on the captions (${e.pct}% of a word)`, soft: (e) => `${e.what} is shown at ${e.pct}% of its file (${e.file}px wide): it will look soft` };
  const faults = runs.filter((e) => e.n >= 3 && e.kind !== 'soft');
  const soft = [...new Map(runs.filter((e) => e.kind === 'soft').map((e) => [e.what, e])).values()];
  for (const e of faults) console.log(`scene ${e.scene + 1}  ${e.from.toFixed(1)}-${e.to.toFixed(1)}s  ` + SAY[e.kind](e) + (process.env.PM_DEBUG && e.r ? '  ' + JSON.stringify(e.r) : ''));
  const cuts = faults.filter((e) => e.kind === 'cut').length;
  console.log(cuts ? cuts + ' cut by the frame' : 'nothing cut by the frame');
  console.log(faults.length - cuts ? (faults.length - cuts) + ' overlap(s) or picture(s) on the captions' : 'no print over another, nothing on the captions');
  for (const e of soft) console.log(`note: scene ${e.scene + 1}  ` + SAY.soft(e));
  process.exit(seen.size || faults.length ? 1 : 0);
}

if (opt.textmap) {
  // the words on screen at each time (PM.textAudit) and the same frame with every word hidden, so the quality check can
  // measure each word against what is really behind it: <out>/textmap.json and <out>/bare_<i>.png
  const dir = path.resolve(opt.out || 'textmap'); fs.mkdirSync(dir, { recursive: true });
  const all = [];
  for (const [i, t] of opt.textmap.entries()) {
    const words = await first.page.evaluate((tt) => window.PM.textAudit(tt), t);
    await first.page.evaluate(() => window.PM.settle && window.PM.settle());   // the clip frame behind the words, decoded
    await first.page.addStyleTag({ content: '#stage, #stage * { color: transparent !important; text-shadow: none !important; -webkit-text-stroke: 0 !important }' });
    await first.page.evaluate(() => new Promise((r) => requestAnimationFrame(() => r())));
    await first.page.screenshot({ path: path.join(dir, 'bare_' + i + '.png'), type: 'png' });
    await first.page.evaluate(() => document.querySelectorAll('style').forEach((s) => { if (s.textContent.includes('color: transparent !important')) s.remove(); }));
    all.push({ t, words });
  }
  fs.writeFileSync(path.join(dir, 'textmap.json'), JSON.stringify(all));
  await browser.close();
  console.log('textmap: ' + all.length + ' frame(s) in ' + dir);
  process.exit(0);
}

if (opt.safe) {
  // words inside the platform's button zones (zones file from director/platforms.py), every 0.2 s; a run shorter
  // than 0.6 s is something passing through (an entrance), not a fault
  const zones = JSON.parse(fs.readFileSync(path.resolve(opt.safe), 'utf8'));
  const hits = [];
  for (let t = 0.05; t < duration; t += 0.2) hits.push(...(await first.page.evaluate(([tt, z]) => window.PM.safeZones(tt, z), [t, zones])));
  await browser.close();
  const runs = [], open = new Map();
  for (const h of hits) {
    const k = h.zone + '|' + h.scene + '|' + h.what, e = open.get(k);
    if (e && h.t - e.to < 0.25) { if (h.t > e.to) e.n++; e.to = h.t; e.pct = Math.max(e.pct, h.pct); }     // n counts samples, not boxes
    else { const r = { ...h, from: h.t, to: h.t, n: 1 }; runs.push(r); open.set(k, r); }
  }
  const found = runs.filter((e) => e.n >= 3);
  for (const e of found) console.log(`safe ${e.hard ? 'HARD' : 'caution'}  scene ${e.scene + 1}  ${e.from.toFixed(1)}-${e.to.toFixed(1)}s  ${e.what} in the ${e.zone} zone (${e.pct}%)`);
  const hard = found.filter((e) => e.hard).length;
  console.log(hard ? hard + ' word(s) under the app\'s buttons' : 'nothing under the app\'s buttons');
  process.exit(hard ? 1 : 0);
}

if (opt.still || opt.sheet) {
  const times = opt.still || Array.from({ length: Math.ceil(duration / opt.every) }, (_, i) => Math.min(duration - 0.05, i * opt.every + 0.01));
  const out = opt.out || (opt.sheet ? 'sheet.png' : 'stills');
  const dir = opt.sheet ? fs.mkdtempSync(path.join(os.tmpdir(), 'pm-sheet-')) : out;
  fs.mkdirSync(dir, { recursive: true });
  const files = [];
  for (const [i, t] of times.entries()) { const f = path.join(dir, 'still_' + String(i).padStart(3, '0') + '_' + t.toFixed(2) + 's.png'); await shot(first.page, t, f, true); files.push(f); }
  await browser.close();
  if (opt.sheet) {
    const cols = Math.min(6, files.length), rows = Math.ceil(files.length / cols);
    const tw = Math.round(270 * (opt.scale >= 1 ? 1 : opt.scale));
    // ffmpeg can't glob with the time suffix reliably, so rename to a plain sequence first
    files.forEach((f, i) => fs.renameSync(f, path.join(dir, 's' + String(i).padStart(3, '0') + '.png')));
    const t = spawnSync(ffmpeg, ['-y', '-v', 'error', '-framerate', '1', '-i', path.join(dir, 's%03d.png'), '-vf', `scale=${tw}:-1,tile=${cols}x${rows}:padding=6:color=black`, '-frames:v', '1', out], { stdio: 'inherit' });
    if (t.status !== 0) die('ffmpeg tile failed');
    console.log('contact sheet: ' + out + '  (' + files.length + ' frames, one every ' + opt.every + 's)');
  } else console.log(files.length + ' still(s) in ' + out + '/');
  process.exit(0);
}

const t0 = opt.from || 0, t1 = Math.min(opt.to || duration, duration);
const total = Math.round((t1 - t0) * fps);
const out = path.resolve(opt.out || 'out.mp4');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'pm-frames-'));
// the frames are removed however the render ends (a failed render once left 2.4 GB behind and filled the disk)
process.on('exit', () => { if (!opt.keep) { try { fs.rmSync(tmp, { recursive: true, force: true }); } catch (e) {} } });
// the frames are encoded in chunks of CHUNK and removed as each chunk is done, so a long film never needs more than
// one chunk of frames on disk (about 0.6 MB each at 1080x1920: a whole 3-minute film is about 3 GB of frames)
const CHUNK = opt.chunk || 900;
try {
  const st = fs.statfsSync(tmp), free = st.bavail * st.bsize, need = Math.min(total, CHUNK) * 0.6e6 * opt.scale * opt.scale / 2.25 * 1.3;
  if (free < need) die(`only ${(free / 1e9).toFixed(1)} GB free for about ${(need / 1e9).toFixed(1)} GB of frames: free some space first`);
} catch (e) { if (String(e.message).includes('GB free')) throw e; }
console.log(`rendering ${total} frames (${t0}s-${t1}s @ ${fps}fps, ${outW}x${outH}) with ${opt.workers} worker(s)...`);
const pages = [first];
for (let k = 1; k < opt.workers; k++) pages.push(await newPage());
let done = 0, lastPct = -1;
const start = Date.now();
// a page wears out over thousands of frames (Chromium then refuses screenshots near the end of a long film): each
// worker starts a fresh page every RECYCLE frames
const RECYCLE = 1200;
const shotCount = pages.map(() => 0), parts = [];
for (let c0 = 0; c0 < total; c0 += CHUNK) {
  const c1 = Math.min(total, c0 + CHUNK);
  await Promise.all(pages.map(async (p, k) => {
    for (let i = c0 + k; i < c1; i += pages.length) {
      if (++shotCount[k] % RECYCLE === 0) { await pages[k].page.context().close(); pages[k] = await newPage(); }
      await shot(pages[k].page, t0 + i / fps, path.join(tmp, 'f_' + String(i).padStart(6, '0') + '.jpg'), false);
      done++;
      const pct = Math.floor((done / total) * 10) * 10;
      if (pct !== lastPct) { lastPct = pct; console.log(`  ${pct}%  (${((Date.now() - start) / 1000).toFixed(0)}s)`); }
    }
  }));
  const part = path.join(tmp, 'part_' + String(parts.length).padStart(3, '0') + '.mp4');
  const pe = spawnSync(ffmpeg, ['-y', '-v', 'error', '-framerate', String(fps), '-start_number', String(c0), '-i', path.join(tmp, 'f_%06d.jpg'),
    '-frames:v', String(c1 - c0), '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', String(opt.crf), '-preset', 'medium', '-r', String(fps), part], { stdio: 'inherit' });
  if (pe.status !== 0) die('ffmpeg encode failed (frames ' + c0 + '-' + c1 + ')');
  parts.push(part);
  if (!opt.keep) for (let i = c0; i < c1; i++) fs.rmSync(path.join(tmp, 'f_' + String(i).padStart(6, '0') + '.jpg'), { force: true });
}
await browser.close();
const video = path.join(tmp, 'video.mp4');
fs.writeFileSync(path.join(tmp, 'parts.txt'), parts.map((f) => `file '${f}'`).join('\n'));
if (spawnSync(ffmpeg, ['-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', path.join(tmp, 'parts.txt'), '-c', 'copy', video], { stdio: 'inherit' }).status !== 0) die('ffmpeg could not join the parts');

// ---------------------------------------------------------------- encode + audio
const D = total / fps;
const args = ['-y', '-v', 'error', '-i', video];
const vg = opt.voiceGain != null ? opt.voiceGain : (sb.audio && sb.audio.voiceGain) || 0;
// the music is heard: about 10 dB under the voice in the pauses and 18-20 dB under it while someone speaks (Étienne's
// mix: at -18 dB and ratio 6 it sat 40 dB under the voice and the film fell silent between sentences).
// storyboard audio.duck = {ratio, threshold, release} overrides these; audio.duck = false keeps the music level.
const au = sb.audio || {}, dk = typeof au.duck === 'object' && au.duck ? au.duck : {};
const duck = !opt.noDuck && au.duck !== false;
const duckRatio = dk.ratio || 3, duckThreshold = dk.threshold || 0.03, duckRelease = dk.release || 400, duckAttack = dk.attack || 40;
const mg = opt.musicGain != null ? opt.musicGain : (au.musicGain != null ? au.musicGain : -6);
// every audio source becomes { f, start, gain(dB), loop?, len? }; start is in output seconds
const srcs = [];
if (audio) {
  if (!fs.existsSync(audio)) die('audio not found: ' + audio);
  const ad = audioDuration(audio);
  if (ad && ad > D + 0.3) console.warn(`warning: voice-over is ${ad.toFixed(1)}s but the storyboard is ${D.toFixed(1)}s. Lengthen scene durations or the end will be cut.`);
  srcs.push({ f: audio, start: 0, gain: vg, voice: true });
}
voiceClips.filter((v) => v.start < t1).forEach((v) => srcs.push({ f: v.f, start: Math.max(0, v.start - t0), gain: vg, voice: true }));
// sound effects: scene.sfx = [{at, name, gain}], scene.beds = [{name, from, to, gain}], automatic paper sounds unless scene.silent
const sfxFile = (name, bed) => {
  const dirs = [path.join(sbDir, 'sfx'), path.join(here, '..', 'assets', 'sfx')];
  // a sound used as a bed loops: its loopable `<name>_bed` take wins when there is one (a passing `train` is one pass,
  // `train_bed` the rumble and wheels that can run under a whole scene)
  if (bed && !name.endsWith('.wav')) for (const d of dirs) { const f = path.join(d, name + '_bed.wav'); if (fs.existsSync(f)) return f; }
  for (const d of dirs) { const f = path.join(d, name.endsWith('.wav') ? name : name + '.wav'); if (fs.existsSync(f)) return f; }
  die('sound effect not found: ' + name + ' (looked in <storyboard>/sfx and the skill assets/sfx)');
};
const autoSfx = !(sb.audio && sb.audio.autoSfx === false);
let sfxCount = 0;
{
  let acc = 0;
  for (const [i, sc] of sb.scenes.entries()) {
    const cues = [];
    if (autoSfx && !sc.silent) {
      if (i > 0 && ['slide', 'push', 'rise', 'drop'].includes(sc.transition || 'slide')) cues.push({ at: 0, name: 'paper_slide', gain: -9 });
      if (sc.banner) cues.push({ at: 0.3, name: 'paper_place', gain: -14 });     // only when a banner really comes in (null = none)
    }
    (sc.sfx || []).forEach((c) => cues.push(c));
    for (const c of cues) { const st = acc + c.at - t0; if (st >= -0.01 && st < t1 - t0) { srcs.push({ f: c.file ? path.resolve(sbDir, c.file) : sfxFile(c.name), start: Math.max(0, st), gain: c.gain != null ? c.gain : -8 }); sfxCount++; } }
    // a bed with `lead` starts that many seconds before its scene's cut (a J-cut: the next place is heard first)
    for (const bd of sc.beds || []) {
      const lead = Math.min(bd.lead || 0, acc + (bd.from || 0)), from = acc + (bd.from || 0) - lead - t0, len = (bd.to != null ? bd.to : sc.dur) - (bd.from || 0) + lead;
      if (from < t1 - t0) srcs.push({ f: sfxFile(bd.name, true), start: Math.max(0, from), gain: bd.gain != null ? bd.gain : -22, loop: true, len, fade: 0.4, fadeIn: Math.max(0.4, lead), settle: bd.settle });
    }
    acc += sc.dur;
  }
}
srcs.forEach((x) => { if (x.loop) args.push('-stream_loop', '-1'); args.push('-i', x.f); });
if (music) { if (!fs.existsSync(music)) die('music not found: ' + music); args.push('-stream_loop', '-1', '-i', music); }
if (srcs.length || music) {
  const chains = [], labels = [];
  srcs.forEach((x, i) => {
    let c = `[${i + 1}:a]`;
    if (x.loop) c += `atrim=0:${x.len.toFixed(3)},asetpts=PTS-STARTPTS,afade=t=in:d=${x.fadeIn || x.fade},afade=t=out:st=${Math.max(0, x.len - x.fade).toFixed(3)}:d=${x.fade},`;
    // a bed sets the place, then settles: settle = {at (s from the bed's start), gain (dB), ramp (s)} (director/studio/mix.py)
    if (x.loop && x.settle && x.settle.gain < x.gain) {
      const a = x.settle.at.toFixed(3), b = (x.settle.at + (x.settle.ramp || 1)).toFixed(3), r = Math.pow(10, (x.settle.gain - x.gain) / 20).toFixed(5);
      c += `volume='if(lt(t,${a}),1,if(lt(t,${b}),1+(${r}-1)*(t-${a})/(${b}-${a}),${r}))':eval=frame,`;
    }
    c += `adelay=${Math.round(x.start * 1000)}:all=1,volume=${x.gain}dB[a${i}]`;
    chains.push(c); labels.push(`[a${i}]`);
  });
  if (music) {
    // the music bed ducks under the voice (sidechain): full level in pauses, ~duck dB lower while someone speaks
    const mi = srcs.length + 1, vl = srcs.map((x, i) => x.voice ? `[a${i}]` : null).filter(Boolean);
    chains.push(`[${mi}:a]volume=${mg}dB,afade=t=in:d=1.5,afade=t=out:st=${Math.max(0, D - 2.5).toFixed(2)}:d=2.5${duck && vl.length ? '[m0]' : '[m]'}`);
    if (duck && vl.length) {
      vl.forEach((l) => labels.splice(labels.indexOf(l), 1));
      chains.push(`${vl.join('')}${vl.length > 1 ? `amix=inputs=${vl.length}:duration=longest:normalize=0,` : ''}asplit=2[vo][vk0]`);
      chains.push('[vk0]apad[vk]');                     // the key runs to the end, so the music does too
      chains.push(`[m0][vk]sidechaincompress=threshold=${duckThreshold}:ratio=${duckRatio}:attack=${duckAttack}:release=${duckRelease}:knee=4[m]`);
      labels.push('[vo]');
    }
    labels.push('[m]');
  }
  chains.push(labels.length === 1 ? `${labels[0]}anull[a]` : `${labels.join('')}amix=inputs=${labels.length}:duration=longest:normalize=0,alimiter=limit=0.89:level=false[a]`);   // a safety limiter only: no AGC in the mix (it lifted every pause back up and undid the duck); the film's two-pass linear loudness sets the level
  args.push('-filter_complex', chains.join(';'), '-map', '0:v', '-map', '[a]');
}
args.push('-c:v', 'copy', '-movflags', '+faststart');                      // the parts are already encoded
if (srcs.length || music) args.push('-c:a', 'aac', '-b:a', '160k');
args.push('-t', D.toFixed(3), out);
const enc = spawnSync(ffmpeg, args, { stdio: 'inherit' });
if (enc.status !== 0) die('ffmpeg encode failed');
if (!opt.keep) fs.rmSync(tmp, { recursive: true, force: true }); else console.log('frames kept in ' + tmp);
const mb = (fs.statSync(out).size / 1048576).toFixed(1);
console.log(`done: ${out}  ${outW}x${outH}  ${D.toFixed(1)}s  ${mb} MB${srcs.length || music ? '' : '  (no audio)'}  (${sfxCount} one-shot sound(s), ${(sfxCount / Math.max(1, D) * 60).toFixed(1)} a minute)`);
