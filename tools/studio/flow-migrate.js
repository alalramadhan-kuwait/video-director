#!/usr/bin/env node
// R7/K3: migrate an existing applied map (studio/flow) to this release. Read-only on its inputs; writes the result for Claude.
//   node flow-migrate.js <studio-flow.json | none> <release dir with flowcore.js + flow-seed.json> <round-0 seed.json> <out dir> [--prev <dir with the live page's flowcore.js + flow-seed.json>]
// - no studio/flow: nothing to do (the page uses its built-in map).
// - no base_acts: the map was applied before this release; it is given the round-0 seed's buttons as its base, so the page hides
//   only the buttons the owner really removed, never the ones this release added.
// - v4/v5: a map is kept only when it is whole, valid, leaves the locked parts alone and names only this build's buttons in
//   base_acts. Otherwise it is refused whole: the result is the built-in map, the old one goes into history, and the report
//   lists every edit of his that the built-in map does not carry (buttons he removed included).
// - v10: when this release itself changed a locked step's text (v10: the review and save rules), a map saved under the live page
//   differs from the new locks only by that. With --prev <the live page's build: flowcore.js + flow-seed.json>, a map whose locked
//   parts are exactly the live page's is honest: its locked steps and arrows become this release's, every step he never edited
//   (the same as the live page's built-in step) becomes this release's too, and every step he did edit stays his.
//   A map that changed the locked parts under the live page too is refused whole, as before.
// - Nothing is written by this script. Claude shows him the dropped edits and writes the result to studio/flow only after his yes.
const fs = require('fs'), path = require('path');
const [, , inFlow, rel, r0Path, out] = process.argv, prevAt = process.argv.indexOf('--prev'), prevDir = prevAt > 0 ? process.argv[prevAt + 1] : null, prevCore = prevDir && path.join(prevDir, 'flowcore.js');
if (!rel || !r0Path || !out) { console.error('usage: flow-migrate.js <studio-flow.json|none> <release dir> <round0 seed> <out dir>'); process.exit(2); }
const core = new Function(fs.readFileSync(path.join(rel, 'flowcore.js'), 'utf8') + ';return {validateFlow, flowRestoreLocks, flowLockDiff, diffFlow, flowClone, flowReadable, flowIsNum, flowIsIso};')();
const seed = JSON.parse(fs.readFileSync(path.join(rel, 'flow-seed.json'), 'utf8')), r0 = JSON.parse(fs.readFileSync(r0Path, 'utf8'));
const acts = (fl) => [...new Set((Array.isArray(fl?.edges) ? fl.edges : []).filter((e) => e && typeof e === 'object').flatMap((e) => [e.act, ...(Array.isArray(e.acts) ? e.acts : [])]).filter((a) => typeof a === 'string'))].sort();
fs.mkdirSync(out, { recursive: true });
const report = [];
if (!inFlow || inFlow === 'none' || !fs.existsSync(inFlow)) { report.push('ما فيه studio/flow: ما يحتاج شي (الاستديو يستخدم المسار اللي فيه).'); fs.writeFileSync(path.join(out, 'flow-migrate-report.md'), report.join('\n') + '\n'); console.log(report[0]); process.exit(0); }
const doc = JSON.parse(fs.readFileSync(inFlow, 'utf8')), had = Array.isArray(doc.base_acts);
const base = had ? doc.base_acts.filter((x) => typeof x === 'string') : acts(r0);
const removed = base.filter((a) => !acts(doc).includes(a));
let lockDiff = core.flowLockDiff(doc).map((x) => x.msg), upgraded = 0;
if (lockDiff.length && prevCore && fs.existsSync(prevCore)) {               // v10: honest under the live page's locks → this release's locks
  const prev = new Function(fs.readFileSync(prevCore, 'utf8') + ';return {flowLockDiff, FLOW_LOCKS};')();
  if (!prev.flowLockDiff(doc, prev.FLOW_LOCKS).length) {
    const lk = seed.nodes.filter((n) => n.locked), lkIds = new Set(lk.map((n) => n.id)), oldIds = new Set(Object.keys(prev.FLOW_LOCKS.nodes));
    const oldEdge = new Set(prev.FLOW_LOCKS.edges.map((x) => x.key)), ek = (e) => JSON.stringify([e.from, e.to, e.label || '', e.act || '', e.kind || '']);
    const up = core.flowClone(doc), pseed = fs.existsSync(path.join(prevDir, 'flow-seed.json')) ? JSON.parse(fs.readFileSync(path.join(prevDir, 'flow-seed.json'), 'utf8')) : { nodes: [] };
    const same = (a, b) => JSON.stringify(a) === JSON.stringify(b), cur = (id) => seed.nodes.find((x) => x.id === id), was = (id) => pseed.nodes.find((x) => x.id === id);
    up.nodes = up.nodes.map((n) => (lkIds.has(n.id) || (was(n.id) && cur(n.id) && same(n, was(n.id))) ? core.flowClone(cur(n.id)) : n)).filter((n) => lkIds.has(n.id) || !oldIds.has(n.id));   // unedited steps follow this release
    for (const n of lk) if (!up.nodes.some((x) => x.id === n.id)) up.nodes.push(core.flowClone(n));
    const before = up.edges.length; up.edges = up.edges.filter((e) => !e.locked);
    for (const e of seed.edges.filter((x) => x.locked)) up.edges.push(core.flowClone(e));
    if (!core.flowLockDiff(up).length) { upgraded = lk.length; doc.nodes = up.nodes; doc.edges = up.edges; lockDiff = []; }
  }
}
// v4 (H1): a map is used only when it is whole, valid and leaves the lock alone; otherwise the built-in map, the old one in history
const errs = lockDiff.length ? [] : ['reel', 'carousel'].flatMap((k) => core.validateFlow(doc, k).filter((x) => x.lv === 'err').map((x) => k + ': ' + x.msg));
let result, mode;
let dropped; try { dropped = [...core.diffFlow(had ? seed : r0, doc), ...removed.map((x) => `شلت زر ${x}`)]; } catch (e) { dropped = ['المسار مو مقروء: ما قدرت أقارنه، كل تعديلاته تحتاج تنعاد يدوي']; }                 // L7: every edit of his that the built-in map will not carry
if (!lockDiff.length && !errs.length) { result = { ...doc, base_acts: [...new Set(base)] }; mode = upgraded ? 'المسار سليم: القواعد الأساسية تحدّثت لهالنسخة، وتعديلاتك باقية (مع base_acts)' : 'المسار سليم: ينحفظ مثل ما هو (مع base_acts)'; }
else {
  mode = had ? 'المسار لمس القواعد الأساسية أو فيه خطأ: نستخدم المسار الأساسي، والقديم ينحفظ بالنسخ' : 'حدّثنا المسار للنسخة اليديدة، وتعديلاتك القديمة محفوظة بالنسخ';
  result = { ...core.flowClone(seed), base_acts: acts(seed), version: (core.flowIsNum(Number(doc.version)) ? Number(doc.version) : 0) + 1, applied_at: new Date().toISOString(), version_note: 'ترحيل: المسار الأساسي (تعديلاتك القديمة بالنسخ)',
    history: [] };
  // v6 (S2): the old map goes into history with checked fields only (a number, a date, a neutral note); never its own text fields
  const old = { version: core.flowIsNum(Number(doc.version)) ? Number(doc.version) : 0, applied_at: core.flowIsIso(doc.applied_at) ? doc.applied_at : null, version_note: 'المسار القبل الترحيل',
    ...(Array.isArray(doc.nodes) && Array.isArray(doc.edges) && JSON.stringify([doc.nodes, doc.edges]).length < 400000 ? { nodes: doc.nodes, edges: doc.edges } : {}) };
  result.history = [old];
}
{ const bad = core.flowReadable(result) || ['reel', 'carousel'].flatMap((k) => core.validateFlow(result, k).filter((x) => x.lv === 'err').map((x) => x.msg))[0];   // v6: the result must pass the page's own check
  if (bad) { console.error('migrated doc would be refused by the page: ' + bad); process.exit(3); } }
fs.writeFileSync(path.join(out, 'studio-flow.migrated.json'), JSON.stringify(result));
report.push(`# flow-migrate dry run`, '', `- input: \`${inFlow}\` (version ${doc.version ?? '?'}, base_acts ${had ? 'present' : 'missing → round-0 buttons'})`,
  `- buttons the owner removed: ${removed.length ? removed.join(', ') : 'none'}${removed.length ? (errs.length ? ' → they come back with the built-in map; Claude asks him once whether to remove them again' : ' → still hidden after migration') : ''}`,
  `- buttons this release adds (never hidden): ${acts(seed).filter((a) => !base.includes(a)).join(', ') || 'none'}`,
  `- locked parts changed in the input: ${lockDiff.length}${lockDiff.length ? '\n  - ' + lockDiff.slice(0, 12).join('\n  - ') + (lockDiff.length > 12 ? `\n  - … +${lockDiff.length - 12}` : '') : ''}`,
  `- result: ${mode}`, `- errors: ${errs.length}${errs.length ? ' (first: ' + errs[0] + ')' : ''}`,
  ...(mode.startsWith('المسار سليم') ? [] : ['', `## His edits the built-in map does not carry (${dropped.length}) — Claude asks him once which to make again`, ...dropped.map((x) => '- ' + x)]), '',
  `Apply: Claude shows the owner the edits above in one message and writes \`studio-flow.migrated.json\` to \`studio/flow\` only after his yes; then marks the matching inbox \`flow_lock-…\` row handled.`);
fs.writeFileSync(path.join(out, 'flow-migrate-report.md'), report.join('\n') + '\n');
console.log(report.join('\n'));
