"""Stage 7: assemble the film from the scenes' chosen versions, render it with the free local engine, review it.

Two reviews are recorded for every film (both are 'review' runs, so their findings flow into the same decisions,
the same Gate 5 and the same final-plan blockers as the classic Studio):
  rv-<render>-cp<n>    the existing independent review (technical, layout, sync, history, readability, style)
  rv-<render>-cp<n>x   the Co-Pilot film checks (opening frame, hook, aspect, silent tail, duration, style
                       consistency, scene issues left, pictures replaced by a fallback) and the AI creative review
"""
from __future__ import annotations
import json, os, re, subprocess

from ..studio import review as RV, storyboard as SB
from . import ai, scenes as SC, styles

FILM_SCALE = float(os.environ.get('VD_FILM_SCALE', '1.5'))
AUTO_FIX = {'TEXT_OVERLAP': {'gap': '1.25'}, 'LONG_HOLD': {'zoom': '1.18'}, 'OPENING_BLANK': {'first_in': 'none'}, 'BLANK_OPENING': {'first_in': 'none'}}


def order(studio, pid, st) -> list[str]:
    from ..studio.voice import approved_script
    sv = approved_script(st)
    return [l['id'] for l in studio.read_json(pid, sv['file'])['lines']] if sv else []


def _probe(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'json', str(path)],
                       capture_output=True, text=True)
    s = json.loads(r.stdout)['streams'][0]
    return s['width'], s['height']


def _tail_db(path, secs=1.2):
    r = subprocess.run(['ffmpeg', '-v', 'info', '-nostats', '-sseof', f'-{secs}', '-i', str(path), '-af', 'volumedetect', '-f', 'null', '-'],
                       capture_output=True, text=True)
    m = re.search(r'max_volume:\s*(-?[\d.]+) dB', r.stderr)
    return float(m.group(1)) if m else None


def assemble(studio, pid, task):
    """Job: one film version from the current scene picks."""
    st = studio.state(pid)
    cp = st['copilot']
    ids = order(studio, pid, st)
    ctx = SC.context(studio, pid, st)
    n = len(cp['films']) + 1
    scenes, t = [], 0.0
    used = {}
    for i, sid in enumerate(ids):
        d = cp['scenes'][sid]
        v = next(x for x in d['versions'] if x['n'] == d['pick']['n'])
        used[sid] = v['n']
        scenes.append({'id': sid, 'line': v['line'], 'start': round(t, 2), 'dur': v['dur'], 'technique': v['technique'], 'theme': v['theme'],
                       'params': v['params'], 'banner': v['banner'], 'take': v['take'],
                       'status': {'voice': 'approved' if st['voice']['takes'].get(v['take'], {}).get('status') == 'approved' else 'not approved',
                                  'art': f'AI reviewed (scene v{v["n"]}); owner approves with the film'},
                       'transition': 'none' if i == 0 else SB.TRANSITION.get(sid, 'cut'), 'concept': None, 'art_version': None})
        t += v['dur']
    from ..studio.voice import approved_script
    sv = approved_script(st)
    hook = ctx['hook']
    doc = {'v': len(st['storyboards']) + 1, 'script_v': sv['v'], 'hook': hook and hook['id'], 'scenes': scenes,
           'endcard': 'timekeeper' if st['brand'] == 'timekeeper' else None, 'endcard_tail': False, 'copilot_film': n}
    rel = studio.put(pid, json.dumps(doc, ensure_ascii=False, indent=1).encode(), 'json')
    rec = {'v': doc['v'], 'file': rel, 'script_v': sv['v'], 'hook': doc['hook'], 'seconds': round(t + 4.5, 2), 'warnings': [],
           'words': None, 'est_final_seconds': None, 'pace': {}, 'copilot_film': n,
           'scenes': [{k: s.get(k) for k in ('id', 'start', 'dur', 'technique', 'take', 'status', 'transition', 'banner', 'concept', 'art_version')} for s in scenes]}
    studio.act(pid, 'storyboard', rec, actor='copilot')
    studio.act(pid, 'cp_film', {'n': n, 'state': 'running', 'storyboard_v': doc['v'], 'scenes': used}, actor='copilot')
    try:
        out = SB.render(studio, pid, task, storyboard_v=doc['v'], scale=FILM_SCALE)
        rid = out['render']
        prof = studio.profile(st['brand']); others = [studio.profile(b) for b in ('timekeeper', 'diabetes-history') if b != st['brand']]
        RV.run(studio, pid, task, render_id=rid, profile=prof, other_profiles=others, research=ctx['research'], label=f'cp{n}')
        st = studio.state(pid)
        r = next(x for x in st['renders'] if x['id'] == rid)
        extra = film_checks(studio, pid, st, r, doc, ctx, n)
        task.unit(what='film checks')
        share = share_copy(studio, pid, r['file'], n)
        st = studio.state(pid)
        fr = {'n': n, 'state': 'ok', 'render': rid, 'render_file': r['file'], 'preview': r.get('preview'), 'poster': r.get('poster'),
              'seconds': r['seconds'], 'storyboard_v': doc['v'], 'scenes': used, 'timeline': r['timeline'] + [{'id': 'endcard', 'start': round(t, 2), 'end': r['seconds']}],
              'base_hashes': {sid: cp['scenes'][sid]['pick']['base_hash'] for sid in ids},
              'reviews': [x['id'] for x in st['review']['runs'] if x['render'] == rid], 'extra': extra, 'share': share,
              'label': 'DRAFT — draft voice (free), AI-reviewed scenes; not for publishing',
              'label_ar': 'مسودة — صوت تجريبي مجاني ومشاهد راجعها الذكاء؛ ليست للنشر'}
        studio.act(pid, 'cp_film', fr, actor='copilot')
        return {'film': n, 'render': rid, 'seconds': r['seconds']}
    except Exception as e:
        studio.act(pid, 'cp_film', {'n': n, 'state': 'failed', 'storyboard_v': doc['v'], 'scenes': used, 'error': f'{type(e).__name__}: {e}'[:400]}, actor='copilot')
        raise


def share_copy(studio, pid, rel, n):
    """A smaller copy to save on the phone and send (about 1.5 Mb/s: a 2½-minute film is about 27 MB, fine for Instagram).
    Free and local; the full-quality film stays the one you review. If it cannot be made, the film is still fine."""
    out = studio.pdir(pid) / 'work' / f'film-cp{n}' / 'share.mp4'
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(studio.path(pid, rel)), '-c:v', 'libx264', '-preset', 'medium', '-crf', '24',
                        '-maxrate', '1400k', '-bufsize', '2800k', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', str(out)],
                       check=True, capture_output=True, timeout=1200)
        return studio.put_file(pid, out, 'mp4')
    except (subprocess.SubprocessError, OSError):
        return None


def film_checks(studio, pid, st, r, doc, ctx, n) -> int:
    video = studio.path(pid, r['file'])
    work = studio.pdir(pid) / 'work' / f'film-cp{n}'
    work.mkdir(parents=True, exist_ok=True)
    F = []

    def add(code, sev, detail, detail_ar, rec, scene=None, t=None, persp='copilot_film'):
        F.append({'code': code, 'severity': sev, 'perspective': persp, 'detail': detail, 'detail_ar': detail_ar, 'recommendation': rec,
                  'scene': scene, 't': None if t is None else round(t, 2), 'fix_stage': 'art'})

    first = RV._still(video, 0.0, work / 'frame0.png')
    if SC._ink(first) < 0.004:
        add('OPENING_BLANK', 'major', 'the first frame (the Reels cover) is an empty page', 'الإطار الأول (غلاف الريلز) صفحة فارغة',
            'show the opening words from frame 0', doc['scenes'][0]['id'], 0.0)
    hook = ctx['hook']
    if not hook or doc['scenes'][0]['line'] != hook['spoken'] or doc['hook'] != hook['id']:
        add('HOOK_MISMATCH', 'critical', 'the film does not open with the approved hook', 'الفيلم لا يبدأ بالافتتاحية المعتمدة',
            'rebuild the opening scene from the approved hook', doc['scenes'][0]['id'], 0.0)
    w, h = _probe(video)
    if abs(w / h - 9 / 16) > 0.01:
        add('ASPECT', 'critical', f'{w}x{h} is not 9:16', f'المقاس {w}x{h} ليس 9:16', 'render at 9:16')
    tail = _tail_db(video, 1.0)                     # more than a second of black silence at the end (the end card's own fade is shorter)
    if tail is not None and tail < -50 and SC._ink(RV._still(video, r['seconds'] - 1.0, work / 'last.png')) < 0.004:
        add('SILENT_TAIL', 'major', f'the last second is black and silent (peak {tail} dB)', 'آخر ثانية سوداء وصامتة', 'end on the end card', None, r['seconds'] - 1.0)
    target = st['copilot']['settings'].get('duration_s') or 75
    if not 0.65 * target <= r['seconds'] <= 1.35 * target:
        add('DURATION_OFF', 'minor', f'{r["seconds"]:.0f} s against a target of {target} s', f'المدة {r["seconds"]:.0f} ث والهدف {target} ث', 'shorten or lengthen the script')
    if ctx['style']:
        ok = {ctx['style']['theme'], *ctx['style'].get('theme_for', {}).values()}
        for s in doc['scenes'][1:]:
            if s['theme'] not in ok and s['technique'] not in ('dark_keynote',):
                add('STYLE_INCONSISTENT', 'minor', f"{s['id']} uses {s['theme']} outside the approved style", 'مشهد خارج ألوان الأسلوب المعتمد',
                    'use the style palette', s['id'], s['start'] + 0.5)
    for s in doc['scenes']:
        pk = st['copilot']['scenes'][s['id']]['pick']
        for f in pk.get('open', []):
            if f['severity'] in ('minor',):
                add('SCENE_' + f['code'], 'minor', f['detail'], f.get('detail_ar', ''), 'kept after the scene review', s['id'], s['start'] + 0.5, 'art_reviewer')
        v = next(x for x in st['copilot']['scenes'][s['id']]['versions'] if x['n'] == pk['n'])
        if v.get('fallback'):
            add('PICTURE_FALLBACK', 'info', v['fallback'], 'لا توجد صورة مرخّصة: استُخدم بديل بلا صور مخترعة', 'add a licensed picture to replace it', s['id'], s['start'] + 0.5)
    tl = [{'id': s['id'], 'start': s['start'], 'end': round(s['start'] + s['dur'], 2)} for s in doc['scenes']]
    cr = ai.call(studio, pid, 'film_review', {'scenes': tl, 'seconds': r['seconds'], 'lines': {s['id']: s['line'] for s in doc['scenes']}})
    for f in cr.get('findings', []):
        add(f.get('code', 'CREATIVE'), f.get('severity', 'minor'), f.get('detail', ''), f.get('detail_ar', ''), f.get('recommendation', 'consider a change'),
            f.get('scene'), f.get('t'), 'ai_film_reviewer')
        F[-1]['label'] = cr.get('label')
    for i, f in enumerate(F):
        f['id'] = f"{r['id']}-cp{n}x-{i + 1:02d}"
        f['evidence'] = studio.put_file(pid, RV._still(video, f['t'] if f['t'] is not None else 0.5, work / 'ev' / f"{f['id']}.jpg"), 'jpg')
    rec = {'id': f"rv-{r['id']}-cp{n}x", 'render': r['id'], 'label': f'cp{n}x', 'platform': 'reels', 'findings': F,
           'contact': next((x['contact'] for x in st['review']['runs'] if x['render'] == r['id']), None), 'scenes': len(doc['scenes']),
           'counts': {s: sum(1 for f in F if f['severity'] == s) for s in ('critical', 'major', 'minor', 'info')}}
    studio.act(pid, 'review', rec, actor='reviewer')
    return len(F)
