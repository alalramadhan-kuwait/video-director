#!/usr/bin/env python3
"""R4: one-time backfill of `approved_version`, BEFORE the new page goes live.

Read-only on its inputs. Writes a batch for Claude to apply, plus a report:
  python3 backfill.py --films <dir of film json> --inbox <dir of inbox json> --out <dir>

Rules:
- posted  -> approved_version = posted.version (or version). The page also treats posted without it as approved.
- done    -> the newest «موافق» row of the finished piece (step «المراجعة» or «التسليم», or the row's own `finished`).
             If its version is the current one: approved_version = version.
             If not, or there is none: state waiting, «نسخة يديدة تنتظر موافقتك», so he approves this version himself.
- a test sample (version «تجربة …»), waiting or working -> nothing (nothing publishable to bless).
- L2: the posted version comes from the «نشرت «…» vN» inbox row when there is one; the report flags a film updated after it
  was posted, and a posted version that is not the last finished approval (for Claude to check by hand).
- L3: a voice with no take_id/takes gets take_id from its current audio file, so the word-fix count has a take to follow.
- Idempotent: a record that already has approved_file is left alone, and an op never rewrites a value the record already
  holds, so it runs again right after the publish with 0 writes.
- v8 (S8): an approval names the FILE. posted -> approved_file (the video, or the slides) only when the record was not changed
  after the post and its version is the posted one; a `final` must be shown to be for the posted version (final_version, or
  a vN in its name, or the very same file as the video): otherwise ⚠ and NO approved_version (gleitze: final
  film/gleitze-v5-full.mp4 under v8). done -> only an approve row that names the current file (v8 `file`, or v7 `seen_src`
  equal to the video) and is newer than media_at counts; else back to waiting, so he approves the file himself.
- v9 (S16): a bare `final` (no version mark) on a film that is not posted is marked so his ordinary save works:
  - the final IS the video: final_version = version, final_from = the video (no media needed);
  - another file: only with --media <dir> (local copies of the files, by path): when its length is within 0.3 s of the
    video's, final_version, final_from = the video and final_hash = its sha256 are written, flagged «Claude: تأكد»;
    otherwise (or without --media) nothing is written and the report lists it as final_needed for Claude.
- v10 (S18): an approval names the exact studio asset ADDRESSES (/_blob/<32 hex>, a new id on every upload, never overwritten):
  every approval op also writes approved_src (a reel) or approved_slides (a carousel) next to approved_file, and --media no longer
  writes final_hash (the page hashes nothing). A record whose media are not assets (a published film/... or carousel/... path, http)
  is listed «media_fix» with its addresses and nothing is written for it: Claude re-uploads them as assets at deploy (live gleitze
  and halter-2 have film/... finals). The page then shows «Claude يرفع الملف من يديد» and writes one media_fix row for an open film.
- v5 (L2): every op is a plain `update` with whole top-level values, so a shallow or a deep merge gives the same record:
  `voice` is the record's own voice object with `take_id` added (never a dotted key), and a waiting film gets a real `changes`
  line ({at, v, what}) in front of its own list. Every op carries `if_version`: the stored version when the dump has one, else
  `sha256:<hash of the record as read>`. Claude re-reads the record just before writing and skips the op if it differs.
- v11 (S23): a record that already carries its approval (approved_version = version, and approved_slides / approved_src, else
  approved_file, equal to the shown asset addresses) is approved, whatever approved_file holds: nothing is written for it (the live
  gphg-prices: approved on the live page with approved_file null). An S19 chat row ({kind: approve, via: chat, version,
  approved_src | approved_slides}) counts as a named approval of the finished piece.
- v11 (S24): no approval is ever written that names an address which is not a studio asset. A film with such media is listed
  «media_fix» only (nothing about its approval or state is written); its approval comes with its re-upload (deploy/reupload.py:
  a posted film is bound to its new addresses in the same write).
"""
import json, glob, os, re, sys, argparse
ap = argparse.ArgumentParser(); ap.add_argument('--films', required=True); ap.add_argument('--inbox', required=True); ap.add_argument('--out', required=True); ap.add_argument('--media')
a = ap.parse_args()
load = lambda p: (lambda j: j.get('data', j))(json.load(open(p)))
import hashlib, datetime
raw = {os.path.basename(p)[:-5]: json.load(open(p)) for p in sorted(glob.glob(os.path.join(a.films, '*.json')))}
films = {k: j.get('data', j) for k, j in raw.items()}
def if_version(fid):                                                  # the version the op was computed from
    j = raw[fid]; v = j.get('_version', j.get('version')) if 'data' in j else j.get('_version')
    return v if v is not None else 'sha256:' + hashlib.sha256(json.dumps(films[fid], ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
NOW = os.environ.get('BACKFILL_NOW') or datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
rows = [load(p) for p in glob.glob(os.path.join(a.inbox, '*.json'))]
FINAL_STEPS = ('المراجعة', 'التسليم')
def posted_row(fid):
    best = None
    for r in rows:
        if r.get('film') != fid or r.get('kind') != 'posted': continue
        m = re.search(r'نشرت «.*?» (\S.*?)\.?$', (r.get('text') or '').strip())
        v = r.get('version') or (m.group(1).strip() if m else None)
        if v and (best is None or r.get('at', '') > best[0]): best = (r.get('at', ''), v)
    return best
def approves(fid):
    out = []
    for r in rows:
        if r.get('film') != fid or r.get('kind') != 'approve': continue
        m = re.search(r'موافق على «.*?» (.*?) \((.*?)\)', r.get('text') or '')
        v = r.get('version') or (m.group(1).strip() if m else None); step = m.group(2) if m else ''
        fin = r.get('finished') if 'finished' in r else step in FINAL_STEPS
        fl = r['file'] if 'file' in r else r.get('seen_src')                # v8: the file he watched
        if r.get('via') == 'chat' and isinstance(r.get('version'), str) and isinstance(r.get('at'), str):   # v11 (S23): his «موافق» in chat (S19)
            sl, sr = r.get('approved_slides'), r.get('approved_src')
            fl = sl if isinstance(sl, list) and all(isinstance(x, str) for x in sl) else sr if isinstance(sr, str) else None
            fin = fl is not None; step = step or 'بالمحادثة'
        out.append({'at': r.get('at', ''), 'version': v, 'finished': fin, 'step': step, 'file': fl, 'via': r.get('via')})
    return sorted(out, key=lambda x: x['at'], reverse=True)
batch, report = [], []
import subprocess, struct
def media_file(u):                                                   # v9: the local copy of a file named by a record, or None
    if not a.media or not isinstance(u, str): return None
    p = os.path.join(a.media, u.split('?')[0].lstrip('/'))
    return p if os.path.isfile(p) else None
def sha_of(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
def duration(p):                                                     # seconds, from ffprobe or the mp4's own mvhd box
    try: return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p], capture_output=True, text=True, check=True).stdout.strip())
    except Exception: pass
    b = open(p, 'rb').read(); i = b.find(b'mvhd')
    if i < 4: return None
    v = b[i + 4]; o = i + 8 + (16 if v == 1 else 8)
    ts = struct.unpack('>I', b[o:o + 4])[0]; du = struct.unpack('>Q', b[o + 4:o + 12])[0] if v == 1 else struct.unpack('>I', b[o + 4:o + 8])[0]
    return du / ts if ts else None
def mark_final(fid, f):                                              # v9 (S16): one op for a bare final on a film that is not posted
    st, v = f.get('state'), f.get('version') or ''
    fin = f.get('final')
    if st == 'posted' or not isinstance(fin, str) or not fin or f.get('final_version') or not v or v.startswith('تجربة'): return
    video = f.get('video') if isinstance(f.get('video'), str) else None
    if fin == video:
        batch.append({'collection': 'films', 'id': fid, 'if_version': if_version(fid), 'update': {'final_version': v, 'final_from': video}})
        report.append((fid, st, v, '—', 'الملف النهائي هو نفس الفيديو اللي يشوفه', f'final_version = {v}, final_from = الفيديو')); return
    pf, pv = media_file(fin), media_file(video)
    if not (pf and pv):
        report.append((fid, st, v, '—', '⚠ final_needed: ملف نهائي بلا علامة، ويحتاج --media عشان نقارنه بالفيديو (أو Claude يعلّمه {url, version, made_from})', 'ولا شي')); return
    df, dv = duration(pf), duration(pv)
    if df is None or dv is None or abs(df - dv) > 0.3:
        report.append((fid, st, v, '—', f'⚠ final_needed: طول الملف النهائي {df} غير طول الفيديو {dv}: Claude يجهّز الصح', 'ولا شي')); return
    h = sha_of(pf)
    batch.append({'collection': 'films', 'id': fid, 'if_version': if_version(fid), 'update': {'final_version': v, 'final_from': video}})   # v10: no final_hash
    report.append((fid, st, v, '—', f'⚠ الملف النهائي بنفس طول الفيديو ({df:.2f} ث): انعلّم له، Claude: تأكد إنه منه', f'final_version = {v}, final_from = الفيديو'))
ASSET = re.compile(r'^/_blob/[0-9a-f]{32}$')
def media_of(f):                                                     # v10 (S18): every media address the page binds to
    fin = f.get('final'); fin = fin.get('url') if isinstance(fin, dict) else fin
    vo = f.get('voice') if isinstance(f.get('voice'), dict) else {}
    out = [x for x in [f.get('video'), fin, vo.get('audio')] if isinstance(x, str) and x]
    if f.get('kind') == 'carousel' and isinstance(f.get('slides'), list): out += [x for x in f['slides'] if isinstance(x, str)]
    return out
for fid, f in films.items():
    bad = [u for u in media_of(f) if not ASSET.match(u)]
    if bad: report.append((fid, f.get('state'), f.get('version') or '', '—', f'⚠ media_fix: {len(set(bad))} ملف مو asset بالاستوديو ({", ".join(sorted(set(bad))[:3])}{"…" if len(set(bad)) > 3 else ""}): Claude يرفعه من يديد كـ asset (عنوان /_blob/ يديد)، والاستديو ما يوافق ولا يحفظ ولا يشارك لين يرفعه', 'ولا شي'))
for fid, f in films.items(): mark_final(fid, f)
for fid, f in films.items():
    st, v = f.get('state'), f.get('version') or ''
    vo = f.get('voice') if isinstance(f.get('voice'), dict) else None
    if vo and vo.get('audio') and vo.get('take_id') is None and vo.get('takes') is None:   # L3
        tid = os.path.basename(str(vo['audio'])).split('?')[0]
        batch.append({'collection': 'films', 'id': fid, 'if_version': if_version(fid), 'update': {'voice': {**vo, 'take_id': tid}}})
        report.append((fid, st, v, '—', 'الصوت ما له رقم تسجيلة', f'voice.take_id = {tid}'))
    if f.get('approved_file') is not None: report.append((fid, st, v, '—', 'عنده approved_file من قبل (v8)', 'ولا شي')); continue
    if any(not ASSET.match(u) for u in media_of(f)):                  # v11 (S24): media_fix only; the approval comes with the re-upload
        report.append((fid, st, v, '—', 'media_fix بس: ما انكتبت موافقة على عنوان مو asset (تنكتب مع إعادة الرفع، deploy/reupload.py)', 'ولا شي')); continue
    shown0 = (f.get('slides') if isinstance(f.get('slides'), list) else None) if f.get('kind') == 'carousel' else (f.get('video') if isinstance(f.get('video'), str) else None)
    rec0 = f.get('approved_slides') if f.get('kind') == 'carousel' else f.get('approved_src')
    if rec0 is None: rec0 = f.get('approved_file')
    if shown0 and v and f.get('approved_version') == v and json.dumps(rec0) == json.dumps(shown0):   # v11 (S23): his approval is on the record
        report.append((fid, st, v, v, 'موافقة مكتوبة بالسجل على نفس الملفات (' + str(f.get('approved_via') or '—') + ')', 'ولا شي')); continue
    if v.startswith('تجربة') or (f.get('flow') or {}).get('mode') == 'sample':
        report.append((fid, st, v, '—', 'تجربة أسلوب: ما تنشر', 'ولا شي')); continue
    def put(upd, why, change):                                        # only the fields whose value changes
        upd = {k: x for k, x in upd.items() if f.get(k, '<none>') != x}
        if upd: batch.append({'collection': 'films', 'id': fid, 'if_version': if_version(fid), 'update': upd})
        report.append((fid, st, v, why[0], why[1], change if upd else 'ولا شي (مكتوب من قبل)'))
    shown = (f.get('slides') if isinstance(f.get('slides'), list) else None) if f.get('kind') == 'carousel' else (f.get('video') if isinstance(f.get('video'), str) else None)
    fin = f.get('final'); fin_url = fin.get('url') if isinstance(fin, dict) else fin if isinstance(fin, str) else None
    fin_ver = fin.get('version') if isinstance(fin, dict) else f.get('final_version')
    tok = lambda x: set(re.findall(r'(?<![a-z0-9])v\d+(?!\d)', str(x or '').lower()))
    if st == 'posted':
        pr = posted_row(fid); pv = (f.get('posted') or {}).get('version') or (pr[1] if pr else None)
        if not pv:                                                    # v7 (L2): the posted version is unknown: write nothing, ask
            report.append((fid, st, v, '—', '⚠ ما أعرف أي نسخة انتشرت (لا posted.version ولا سطر «نشرت»): ما انكتب شي، اسأله', 'ولا شي')); continue
        flags = []
        pat = (f.get('posted') or {}).get('at') or (pr[0] if pr else '')
        late = bool(pat and (f.get('updated') or '') > pat)
        if late: flags.append(f'⚠ تحدّث بعد النشر ({(f.get("updated") or "")[:16]}): الملف مو أكيد اللي انتشر، يوافق من يديد')
        fa = [x for x in approves(fid) if x['finished']]
        if fa and fa[0]['version'] != pv: flags.append(f'⚠ آخر موافقة على {fa[0]["version"]}، والمنشور {pv}')
        if pv != v: flags.append(f'⚠ النسخة الحالية {v} غير المنشورة: تبقى مقفولة لين يوافق')
        name = str(fin_url or '').split('?')[0].split('/')[-1]
        if fin_url:                                                   # v8 (S8): is the final the posted version's file?
            if isinstance(fin_ver, str): fin_ok, known = fin_ver == pv, True
            elif tok(name): fin_ok, known = tok(name) <= tok(pv) and bool(tok(pv)), True
            else: fin_ok, known = fin_url == shown and not late and pv == v, False
            if not fin_ok:
                what = f'الملف النهائي ({name}) مو لنسخة {pv}' if known else f'ما أقدر أثبت إن الملف النهائي ({name}) لنسخة {pv}'
                report.append((fid, st, v, pv, f'⚠ {what}: ما انكتب approved_version. Claude يجهّز الملف النهائي لـ {pv} (final_version)، وهو يوافق عليه' + ('؛ ' + '؛ '.join(flags) if flags else ''), 'ولا شي'))
                if f.get('approved_version') is not None: put({'approved_version': None}, (pv, '⚠ approved_version كان مكتوب والملف النهائي مو له'), 'approved_version = null')
                continue
        upd = {'approved_version': pv}
        if not late and pv == v and shown:
            upd.update({'approved_file': shown, ('approved_slides' if f.get('kind') == 'carousel' else 'approved_src'): shown, 'approved_at': pat or NOW, 'approved_media': f.get('media_at') if isinstance(f.get('media_at'), str) else ''})
            if fin_url and not isinstance(fin_ver, str): upd['final_version'] = pv
        put(upd, (pv, 'منشور: ' + ('من سطر «نشرت»' if pr else 'النسخة الحالية') + ('؛ ' + '؛ '.join(flags) if flags else '')), ', '.join(f'{k} = {json.dumps(x, ensure_ascii=False)[:60]}' for k, x in upd.items()))
        continue
    if st == 'done':
        ok = [x for x in approves(fid) if x['finished']]
        r0 = ok[0] if ok else None
        named = r0 and r0['version'] == v and r0.get('file') is not None and json.dumps(r0['file']) == json.dumps(shown)
        fresh = r0 and (not isinstance(f.get('media_at'), str) or r0['at'] > f['media_at'])
        if named and fresh and shown:
            put({'approved_version': v, 'approved_file': shown, ('approved_slides' if f.get('kind') == 'carousel' else 'approved_src'): shown, 'approved_at': r0['at'], 'approved_media': f.get('media_at') if isinstance(f.get('media_at'), str) else ''},
                (r0['version'], f'آخر «موافق» على النسخة الخالصة وعلى نفس الملف ({r0["at"][:16]})'), f'approved_version = {v}, approved_file')
        else:
            why = (f'آخر «موافق» كان على {r0["version"]}' if r0 and r0['version'] != v else 'آخر «موافق» ما يسمّي الملف اللي يشوفه الحين' if r0 else 'ما لقيت «موافق» على النسخة الخالصة')
            line = {'at': NOW, 'v': v, 'what': [f'الاستديو صار يربط الموافقة بالملف نفسه: {why}، فهالنسخة تنتظر موافقتك']}
            put({'state': 'waiting', 'waiting': 'نسخة يديدة تنتظر موافقتك', 'changes': [line, *(f.get('changes') or [])]}, (r0['version'] if r0 else '—', why), 'state = waiting (يوافق بنفسه)')
        continue
    report.append((fid, st, v, '—', 'ما وافق للحين', 'ولا شي'))
# v6 (L5): one update per film. Two ops on one record would share one if_version, and the second would always look stale.
merged = {}
for op in batch:
    m = merged.setdefault(op['id'], {'collection': op['collection'], 'id': op['id'], 'if_version': op['if_version'], 'update': {}})
    assert m['if_version'] == op['if_version'] and not (set(m['update']) & set(op['update'])), ('two ops clash on', op['id'])
    m['update'].update(op['update'])
batch = list(merged.values())
for op in batch:                                                      # v11 (S24): never an approval naming a non-asset address
    for k in ('approved_src', 'approved_slides', 'approved_file'):
        x = op['update'].get(k)
        assert x is None or all(isinstance(y, str) and ASSET.match(y) for y in (x if isinstance(x, list) else [x])), ('non-asset approval', op['id'], k)
os.makedirs(a.out, exist_ok=True)
json.dump({'note': 'R4 backfill: apply BEFORE the new page goes live, and again right after it. Each op: re-read films/<id>; if its version (or sha256 of the record) differs from if_version, skip it and re-run the backfill; else update with these whole top-level values', 'ops': batch}, open(os.path.join(a.out, 'backfill-batch.json'), 'w'), ensure_ascii=False, indent=1)
md = ['# Backfill dry run (approved_version)', '', f'Inputs (read-only): `{a.films}`, `{a.inbox}`. {len(films)} films, {len(rows)} inbox rows. {len(batch)} writes.', '',
      '| الفلم | الحالة | النسخة | آخر نسخة وافق عليها | ليش | التغيير |', '|---|---|---|---|---|---|'] + [f'| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} |' for r in report]
open(os.path.join(a.out, 'backfill-report.md'), 'w').write('\n'.join(md) + '\n')
import html as _h
E = lambda x: _h.escape(str(x), quote=True)   # v7 (L2): every cell is text
rowsh = ''.join(f'<tr><td dir="ltr">{E(r[0])}</td><td>{E(r[1])}</td><td>{E(r[2])}</td><td>{E(r[3])}</td><td>{E(r[4])}</td><td><b>{E(r[5])}</b></td></tr>' for r in report)
open(os.path.join(a.out, 'backfill-report.html'), 'w').write(f'''<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Backfill dry run</title>
<style>body{{font:15px/1.5 system-ui,sans-serif;margin:16px;background:#FBF7EF;color:#222}}table{{border-collapse:collapse;width:100%;font-size:12px}}td,th{{border:1px solid #D9CFB8;padding:5px;text-align:right;vertical-align:top}}th{{background:#F2C230}}</style>
<h1 style="font-size:19px">تجربة الترحيل: «النسخة اللي وافقت عليها»</h1><p>{len(films)} فلم · {len(rows)} سطر · {len(batch)} تغيير. ما انكتب شي؛ هذي قائمة اللي بيصير.</p>
<table><tr><th>الفلم</th><th>الحالة</th><th>النسخة</th><th>آخر موافقة</th><th>ليش</th><th>التغيير</th></tr>{rowsh}</table></html>''')
print(f'{len(films)} films, {len(batch)} writes ({sum(len(o["update"]) for o in batch)} fields) -> {a.out}')
