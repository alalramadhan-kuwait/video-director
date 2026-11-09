#!/usr/bin/env python3
"""v11 (S24): checklist §5 step 6, the re-upload of media that are not studio assets. A dry run: it reads local copies and writes
the exact ops to a file; nothing is uploaded and no database is touched. Claude applies the ops (one `update` per film) after
uploading each listed file as a new studio asset.

  python3 reupload.py --films <dir of film json, as read right before the re-upload> --map <map.json> --out <dir> [--inbox <dir>]

<map.json> is {"<old path>": "/_blob/<32 hex>", ...}: every old path (a published film/… or carousel/… path) and the new asset id
its upload got. Re-uploading a file gives the same bytes at a new, immutable address, so:
- every media field that names a mapped path is rewritten to its new address, in one write per film, with media_at:
  `video`, each of `slides`, `voice.audio` and `final` (written as {url, version, made_from}; a `final` that was the video itself
  becomes {url: <new video>, version, made_from: <new video>}; other marks are carried, never invented);
- a POSTED film is bound in the same write (M3): approved_version = the posted version, approved_src (a reel) or approved_slides
  (a carousel) and approved_file = the new shown addresses, approved_via 'reupload', approved_at, approved_media. Only when the
  posted version is known and is the record's version; a posted film whose final is not shown to be the posted version's
  (live gleitze: film/gleitze-v5-full.mp4 under v8) is refused whole and listed, so nothing is bound to the wrong file;
- an open film gets its new addresses only; he approves them on the page.
Refused (nothing written, listed): a film with a non-asset address the map does not cover, a map value that is not
/_blob/<32 hex>. Idempotent: on its own applied output the old paths are gone, so a re-run writes 0 ops; every op carries
if_version as backfill.py does (re-read the record, `check-version.py`, skip on «changed»).
"""
import json, glob, os, re, hashlib, datetime, argparse, html as _h
ap = argparse.ArgumentParser(); ap.add_argument('--films', required=True); ap.add_argument('--map', required=True); ap.add_argument('--out', required=True); ap.add_argument('--inbox')
a = ap.parse_args()
ASSET = re.compile(r'^/_blob/[0-9a-f]{32}$')
NOW = os.environ.get('BACKFILL_NOW') or datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
raw = {os.path.basename(p)[:-5]: json.load(open(p)) for p in sorted(glob.glob(os.path.join(a.films, '*.json')))}
films = {k: j.get('data', j) for k, j in raw.items()}
rows = [(lambda j: j.get('data', j))(json.load(open(p))) for p in glob.glob(os.path.join(a.inbox, '*.json'))] if a.inbox else []
MAP = json.load(open(a.map))
bad_map = sorted(k for k, x in MAP.items() if not (isinstance(x, str) and ASSET.match(x)))
def if_version(fid):
    j = raw[fid]; v = j.get('_version', j.get('version')) if 'data' in j else j.get('_version')
    return v if v is not None else 'sha256:' + hashlib.sha256(json.dumps(films[fid], ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
def posted_version(fid, f):
    pv = (f.get('posted') or {}).get('version') if isinstance(f.get('posted'), dict) else None
    if isinstance(pv, str) and pv: return pv
    best = None
    for r in rows:
        if r.get('film') != fid or r.get('kind') != 'posted': continue
        m = re.search(r'نشرت «.*?» (\S.*?)\.?$', (r.get('text') or '').strip()); v = r.get('version') or (m.group(1).strip() if m else None)
        if v and (best is None or r.get('at', '') > best[0]): best = (r.get('at', ''), v)
    return best[1] if best else None
tok = lambda x: set(re.findall(r'(?<![a-z0-9])v\d+(?!\d)', str(x or '').lower()))
ops, report = [], []
for fid, f in films.items():
    st, v, car = f.get('state'), f.get('version') or '', f.get('kind') == 'carousel'
    vo = f.get('voice') if isinstance(f.get('voice'), dict) else None
    fin = f.get('final'); fin_o = fin if isinstance(fin, dict) else None; fin_url = fin_o.get('url') if fin_o else fin if isinstance(fin, str) else None
    video = f.get('video') if isinstance(f.get('video'), str) else None
    slides = [x for x in f['slides'] if isinstance(x, str)] if car and isinstance(f.get('slides'), list) else None
    media = [x for x in [video, fin_url, vo.get('audio') if vo else None] if isinstance(x, str) and x] + (slides or [])
    old = [u for u in media if not ASSET.match(u)]
    if not old: continue                                               # all assets already: nothing to do (a re-run lands here)
    miss = sorted({u for u in old if u not in MAP or u in bad_map})
    if miss: report.append((fid, st, v, f'⚠ ما انرفع: {len(miss)} ملف مو بالقائمة أو عنوانه مو /_blob/ ({", ".join(miss[:3])})', 'ولا شي')); continue
    nu = lambda u: MAP.get(u, u) if isinstance(u, str) else u
    pv = posted_version(fid, f) if st == 'posted' else None
    if st == 'posted':
        fin_ver = fin_o.get('version') if fin_o else f.get('final_version')
        name = str(fin_url or '').split('?')[0].split('/')[-1]
        if fin_url and fin_url != video and not (fin_ver == pv if isinstance(fin_ver, str) else bool(tok(name)) and tok(name) <= tok(pv)):
            report.append((fid, st, v, f'⚠ منشور {pv}، والملف النهائي ({name}) مو مبيّن إنه لنسخة {pv}: ما انرفع ولا انربط. يترفع بس ملف {pv} النهائي نفسه', 'ولا شي')); continue
    upd = {}
    if video and video in MAP: upd['video'] = nu(video)
    if slides and any(u in MAP for u in slides): upd['slides'] = [nu(u) for u in f['slides']]
    if vo and isinstance(vo.get('audio'), str) and vo['audio'] in MAP: upd['voice'] = {**vo, 'audio': nu(vo['audio'])}
    if fin_url and fin_url in MAP:
        if fin_url == video: upd['final'] = {'url': nu(video), 'version': (fin_o or {}).get('version') or (f.get('final_version') if isinstance(f.get('final_version'), str) else None) or (pv or v), 'made_from': nu(video)}
        elif fin_o: upd['final'] = {**fin_o, 'url': nu(fin_url), 'made_from': nu(fin_o.get('made_from'))}
        else: upd['final'] = {'url': nu(fin_url), 'version': f.get('final_version') if isinstance(f.get('final_version'), str) else None, 'made_from': nu(f.get('final_from'))}
    upd['media_at'] = NOW
    shown = upd.get('slides', slides) if car else upd.get('video', video)
    bound = ''
    if st == 'posted':
        if not pv: bound = '⚠ ما أعرف أي نسخة انتشرت: انرفع بدون ربط، اسأله'
        elif pv != v: bound = f'⚠ المنشور {pv} والنسخة الحالية {v}: انرفع بدون ربط'
        elif shown and all(isinstance(u, str) and ASSET.match(u) for u in (shown if car else [shown])):
            upd.update({'approved_version': pv, ('approved_slides' if car else 'approved_src'): shown, 'approved_file': shown, 'approved_via': 'reupload', 'approved_at': NOW, 'approved_media': NOW})
            late = (f.get('posted') or {}).get('at') if isinstance(f.get('posted'), dict) else None
            bound = f'منشور {pv}: انربط بالعناوين اليديدة (نفس الملف المنشور)' + (f'؛ ⚠ تحدّث بعد النشر ({str(f.get("updated"))[:16]}): تأكد إن الملف اللي انرفع هو المنشور' if late and (f.get('updated') or '') > late else '')
    else: bound = 'مفتوح: العناوين بس، وهو يوافق عليها بالاستديو'
    ops.append({'collection': 'films', 'id': fid, 'if_version': if_version(fid), 'update': upd})
    report.append((fid, st, v, bound, ', '.join(sorted(upd))))
for op in ops:                                                         # never an approval on a non-asset address
    for k in ('approved_src', 'approved_slides', 'approved_file'):
        x = op['update'].get(k)
        assert x is None or all(isinstance(y, str) and ASSET.match(y) for y in (x if isinstance(x, list) else [x])), ('non-asset approval', op['id'], k)
os.makedirs(a.out, exist_ok=True)
json.dump({'note': '§5 step 6 (v11): upload every old path in the map as a new studio asset first; then, for each op, re-read films/<id>, run check-version.py against if_version (skip and re-run on «changed»), and update with these whole top-level values. Then re-run backfill.py (0 writes expected for these films).', 'ops': ops},
          open(os.path.join(a.out, 'reupload-batch.json'), 'w'), ensure_ascii=False, indent=1)
md = ['# Re-upload dry run (§5 step 6)', '', f'Inputs (read-only): `{a.films}`, `{a.map}`. {len(films)} films, {len(MAP)} mapped paths. {len(ops)} writes.' + (f' ⚠ map values that are not /_blob/<32 hex>: {", ".join(bad_map)}' if bad_map else ''), '',
      '| الفلم | الحالة | النسخة | الربط | الحقول |', '|---|---|---|---|---|'] + [f'| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} |' for r in report]
open(os.path.join(a.out, 'reupload-report.md'), 'w').write('\n'.join(md) + '\n')
E = lambda x: _h.escape(str(x), quote=True)
open(os.path.join(a.out, 'reupload-report.html'), 'w').write('<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Re-upload dry run</title>'
    '<style>body{font:15px/1.5 system-ui,sans-serif;margin:16px;background:#FBF7EF;color:#222}table{border-collapse:collapse;width:100%;font-size:12px}td,th{border:1px solid #D9CFB8;padding:5px;text-align:right;vertical-align:top}th{background:#F2C230}</style>'
    f'<h1 style="font-size:19px">إعادة الرفع: تجربة</h1><p>{len(ops)} تغيير. ما انكتب شي.</p><table><tr><th>الفلم</th><th>الحالة</th><th>النسخة</th><th>الربط</th><th>الحقول</th></tr>'
    + ''.join(f'<tr><td dir="ltr">{E(r[0])}</td><td>{E(r[1])}</td><td>{E(r[2])}</td><td>{E(r[3])}</td><td dir="ltr">{E(r[4])}</td></tr>' for r in report) + '</table></html>')
print(f'{len(films)} films, {len(ops)} writes -> {a.out}')
