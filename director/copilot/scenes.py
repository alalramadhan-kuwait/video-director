"""Stage 6: scene-by-scene production. For each scene: assemble → render frames and a motion clip → technical
check → independent art review → safe fixes → re-render, at most `max_rounds` correction rounds → keep the best
version with its evidence → next scene. No owner pause per scene; the Co-Pilot stops and asks only for a critical
factual problem, unresolved rights, a problem it cannot fix safely, a change that would touch the approved script or
style, or when the retry limit is reached. Every version and its evidence is kept.

A scene version is "AI reviewed", never "approved": the owner approves scenes only as part of the film (Gate 5).
"""
from __future__ import annotations
import copy, hashlib, json, os, re, shutil, subprocess
from pathlib import Path

import numpy as np

from ..studio import art, engine, review as RV
from ..studio.storyboard import VOICE_AT, TAIL
from . import ai, styles
from .factcheck import assertions, subject_hits

SAFE_AI = {'text_size', 'zoom', 'slower', 'gap', 'first_in'}          # what the Co-Pilot may change on its own
OWNER_KEYS = SAFE_AI | {'theme', 'banner'}                              # what an owner comment or decision may change
SEV = {'critical': 100, 'major': 10, 'minor': 1, 'info': 0}
YEAR = re.compile(r'(1[89]\d\d|20\d\d)')
CLIP_SCALE = float(os.environ.get('VD_SCENE_CLIP_SCALE', '0.5'))


def _h(x) -> str:
    return hashlib.sha256(json.dumps(x, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()[:16]


# ====================================================================== what the scene is
def context(studio, pid, st) -> dict:
    """Everything scene specs depend on, read once."""
    from ..studio.voice import approved_script
    cp = st['copilot']
    sv = approved_script(st)
    lines = studio.read_json(pid, sv['file'])['lines'] if sv else []
    brief = studio.read_json(pid, st['art']['brief']) if st['art'].get('brief') else None
    g4 = next((g for g in reversed(cp['gates']['G4']) if g['decision'] == 'approved'), None)
    style = styles.get(g4['style']['id'], g4['style']['version']) if g4 else None
    verified = {a['slot']: a for a in cp['assets'].values() if a['status'] == 'verified' and a.get('slot')}
    hook = next((o for o in st['hooks']['options'] if o['id'] == st['hooks']['selected']), None)
    owner = {}
    for t in cp['tasks']:
        if t.get('scene') and t.get('changes') and t['status'] in ('applied', 'open_applied', 'done'):
            owner.setdefault(t['scene'], {}).update(t['changes'])
    for x in cp['exceptions']:
        if x.get('scene') and x['status'] == 'decided' and x.get('changes'):
            owner.setdefault(x['scene'], {}).update(x['changes'])
    return {'lines': lines, 'brief': brief, 'style': style, 'style_ref': g4 and g4['style'], 'verified': verified, 'hook': hook,
            'owner': owner, 'research': studio.research(pid), 'brand': st['brand']}


def base(studio, pid, st, ctx, sid) -> dict:
    """The scene before any automatic fix. Its hash is what makes a scene version valid or outdated."""
    i = next(k for k, l in enumerate(ctx['lines']) if l['id'] == sid)
    ln = ctx['lines'][i]
    brief = ctx['brief']
    bkey = sid if sid in brief['scenes'] else ('h' if ln.get('role') == 'hook' else sid)
    bs = {**brief['scenes'][bkey], '_id': sid}
    hv = brief.get('hook_visuals', {}).get(ctx['hook']['id']) if (ln.get('role') == 'hook' and ctx['hook']) else None
    c = styles.choose(ctx['style'], bs, ctx['verified'], hv)
    vl = (st['voice'].get('lines') or {}).get(sid, {})
    take = st['voice']['takes'].get(vl.get('take')) if vl.get('take') else None
    banner = None if ln.get('role') == 'hook' or c.get('banner_off') else bs.get('banner')
    if hv and c['technique'] != 'kinetic_type': banner = ctx['hook'].get('on_screen')
    own = ctx['owner'].get(sid, {})
    if own.get('banner') == 'none': banner = None
    return {'scene': sid, 'index': i, 'opening': i == 0, 'line': ln['text'], 'role': ln.get('role'), 'beat': bs.get('beat'),
            'technique': c['technique'], 'params': c['params'], 'theme': c['theme'], 'fallback': c['fallback'], 'assets': c['assets'],
            'banner': banner, 'take': take and take['id'], 'take_status': take and take['status'],
            'dur': round(VOICE_AT + take['seconds'] + TAIL, 2) if take else bs.get('dur', 5.0),
            'style': ctx['style_ref'] and {'id': ctx['style_ref']['id'], 'version': ctx['style_ref']['version']},
            'text_scale': ctx['style'].get('text_scale', 1.0), 'owner_changes': {k: v for k, v in own.items()},
            'asset_files': {a: ctx['verified'][a]['file'] for a in c['assets'] if a in ctx['verified']}}


def base_hash(b) -> str:
    return _h({k: b[k] for k in ('scene', 'opening', 'line', 'technique', 'params', 'theme', 'banner', 'take', 'dur', 'style',
                                 'text_scale', 'owner_changes', 'asset_files')})


def apply(b: dict, changes: dict) -> dict:
    """The scene with changes applied (style text scale, owner changes, then automatic fixes)."""
    p, th = copy.deepcopy(b['params']), b['theme']
    if b['text_scale'] != 1.0:
        p, th = art.apply_changes(p, th, {'text_size': b['text_scale']})
    allc = {**b['owner_changes'], **changes}
    std = {k: v for k, v in allc.items() if k in ('theme', 'text_size', 'zoom', 'slower')}
    if std:
        p, th = art.apply_changes(p, th, std)
    if b['technique'] in ('kinetic_type', 'dark_keynote'):
        if 'zoom' in allc: p['zoom'] = round(1.07 * float(allc['zoom']), 3)          # the type card's slow push
        if 'gap' in allc:
            for ln in p.get('lines', []): ln['gap'] = round(ln.get('gap', ln.get('size', 66) * 1.9) * float(allc['gap']))
            if p.get('stamp'): p['stamp'] = {**p['stamp'], 'y': p['stamp'].get('y', 860) + 60}
        if b['opening'] or allc.get('first_in') == 'none':                         # the first frame of the film is never blank
            for ln in p.get('lines', []):
                if ln.get('at', 0.0) <= 0.3: ln['in'] = 'none'
    return {**b, 'params': p, 'theme': th, 'changes': changes}


def visual(sp, brand) -> dict:
    sc = art.scene_visual(sp['technique'], sp['params'], sp['theme'], sp['dur'], sp['banner'])
    sc.update({'id': sp['scene'], 'dur': sp['dur'], 'transition': 'cut',
               'status': 'METAPHOR' if sp['technique'] in ('kinetic_type', 'paper_cut', 'parallax_25d') else 'CONFIRMED'})
    return sc


# ====================================================================== drawing it
def _ink(png: Path) -> float:
    """Share of the frame that differs from the paper (0 = an empty page)."""
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(png), '-vf', 'scale=180:-2', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'],
                         capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.uint8).astype(int)
    return float(np.mean(np.abs(a - np.median(a)) > 40)) if len(a) else 0.0


def _mean_db(f: Path) -> float | None:
    r = subprocess.run(['ffmpeg', '-v', 'info', '-nostats', '-i', str(f), '-af', 'volumedetect', '-f', 'null', '-'], capture_output=True, text=True)
    m = re.search(r'mean_volume:\s*(-?[\d.]+) dB', r.stderr)
    return float(m.group(1)) if m else None


def materialize(studio, pid, st):
    """Put the project's verified pictures where the engine reads them (assets/<slot>). Unverified ones never go there."""
    adir = studio.pdir(pid) / 'assets'
    for a in st['copilot']['assets'].values():
        if a['status'] == 'verified' and a.get('slot') and a.get('file'):
            src = studio.path(pid, a['file'])
            dst = adir / (a['slot'] + src.suffix)
            if not dst.exists():
                adir.mkdir(parents=True, exist_ok=True); shutil.copyfile(src, dst)


def draw(studio, pid, st, sp, work: Path) -> dict:
    work.mkdir(parents=True, exist_ok=True)
    (work / 'voice').mkdir(exist_ok=True)
    adir = studio.pdir(pid) / 'assets'
    if adir.exists():
        (work / 'assets').mkdir(exist_ok=True)
        for f in adir.glob('*'): shutil.copyfile(f, work / 'assets' / f.name)
    sc = visual(sp, st['brand'])
    if sp['take']:
        tk = st['voice']['takes'][sp['take']]
        shutil.copyfile(studio.path(pid, tk['wav']), work / 'voice' / f"{sp['scene']}.wav")
        sc['voice'] = f"voice/{sp['scene']}.wav"; sc['voiceAt'] = VOICE_AT
        sc['words'] = [[round(VOICE_AT + w['s'], 2), w['w']] for w in tk['words']]
    else:
        sc['captions'] = sp['line']
    sb = {'width': 720, 'height': 1280, 'fps': 30, 'dir': 'rtl', **art.style(st['brand']), 'scenes': [sc]}
    chk = [l for l in engine.check(sb, work) if l.strip().startswith('scene ')]
    d = sp['dur']
    times = [0.0, round(d * 0.35, 2), round(d * 0.7, 2), round(max(0.0, d - 0.15), 2)]
    files = engine.stills(sb, work, times, scale=0.4)               # in the scene's folder: voice/ and assets/ are relative to it
    ink0 = _ink(files[0])
    stills = [studio.put_file(pid, f, 'png') for f in files]
    sbp = work / 'scene.json'; sbp.write_text(json.dumps(sb, ensure_ascii=False), encoding='utf-8')
    clip = work / 'clip.mp4'
    engine.video(sbp, clip, scale=CLIP_SCALE, workers=2)
    webm = work / 'clip.webm'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(clip), '-c:v', 'libvpx-vp9', '-b:v', '600k', '-deadline', 'realtime', '-cpu-used', '8',
                    '-row-mt', '1', '-c:a', 'libopus', '-b:a', '64k', str(webm)], check=True)
    return {'sc': sc, 'check': chk, 'stills': stills, 'times': times, 'ink0': round(ink0, 4), 'clip': studio.put_file(pid, clip, 'mp4'),
            'clip_webm': studio.put_file(pid, webm, 'webm'), 'voice_db': _mean_db(clip) if sp['take'] else None,
            'engine_scene': studio.put(pid, json.dumps(sc, ensure_ascii=False).encode(), 'json')}


# ====================================================================== checking it
def _f(code, sev, detail, detail_ar, fix=None, by='rules'):
    return {'code': code, 'severity': sev, 'detail': detail, 'detail_ar': detail_ar, 'fix': fix, 'by': by}


def tech_checks(sp, drawn, research) -> list[dict]:
    sc, F = drawn['sc'], []
    kinetic = sp['technique'] in ('kinetic_type', 'dark_keynote')
    for l in drawn['check']:
        F.append(_f('LAYOUT', 'major', l.strip(), 'مشكلة في التخطيط: ' + l.strip()[:80]))
    for s, e1, e2, pct in RV._text_overlaps([{'id': sp['scene'], 'start': 0, 'src': sc}]):
        F.append(_f('TEXT_OVERLAP', 'major', f"«{str(e1.get('text'))[:20]}» and «{str(e2.get('text'))[:20]}» overlap ({pct}%)", 'نصّان متداخلان',
                    {'gap': '1.25'} if kinetic else None))
    for s, e, pct in RV._frame_geometry([{'id': sp['scene'], 'start': 0, 'src': sc}]):
        F.append(_f('CUT_BY_FRAME', 'major', f"{e['type']} is {pct}% outside the frame", 'عنصر خارج الإطار'))
    if sp['opening'] and drawn['ink0'] < 0.004:
        F.append(_f('BLANK_OPENING', 'major', 'the first frame of the film is an empty page', 'الإطار الأول من الفيلم صفحة فارغة',
                    {'first_in': 'none'} if kinetic else None))
    if sp['banner'] and len(sp['banner'].split()) > 6:
        F.append(_f('BANNER_LONG', 'minor', f"banner has {len(sp['banner'].split())} words", 'العنوان طويل'))
    rtext = json.dumps(research or {}, ensure_ascii=False)
    texts = [sp['banner'] or ''] + [str(e.get('text') or e.get('title') or e.get('label') or '') for e in sc.get('elements', [])]
    for tx in texts:
        for y in YEAR.findall(tx):
            if y not in rtext:
                F.append(_f('YEAR_NOT_IN_RESEARCH', 'critical', f'«{tx}» shows {y}, which the research does not support', f'سنة {y} غير موجودة في البحث'))
    on_screen = ' . '.join(t for t in texts if t)
    for x in assertions(on_screen):
        if not x['attributed'] and not x['negated'] and x['kind'] != 'first_time' and subject_hits(x['clause'], research):
            F.append(_f('CLAIM_ON_SCREEN', 'critical', f'on-screen text «{x["clause"][:40]}» states what the research marks avoid', 'نص على الشاشة يقول ادعاءً مرفوضًا'))
    for e in sc.get('elements', []):
        if e.get('silhouette'):
            F.append(_f('PLACEHOLDER_PERSON', 'major', 'a placeholder stands in for a real person', 'ظلّ بديل مكان شخص حقيقي'))
    if sp['take'] and (drawn['voice_db'] is None or drawn['voice_db'] < -45):
        F.append(_f('VOICE_MISSING', 'critical', f"the voice is not audible in the scene clip ({drawn['voice_db']} dB)", 'الصوت غير مسموع في المشهد'))
    moving = sc.get('camera') or any(isinstance(e.get(k), list) for e in sc.get('elements', []) for k in ('x', 'y', 'scale', 'view'))
    if sp['dur'] > 8 and not moving:
        F.append(_f('LONG_HOLD', 'minor', f"{sp['dur']:.1f} s without movement", 'مشهد طويل بلا حركة', {'zoom': '1.18'} if kinetic else None))
    if sp.get('fallback'):
        F.append(_f('FALLBACK', 'info', sp['fallback'], 'بديل: لا توجد صورة مرخّصة لهذا المشهد'))
    return F


def _effective(b, changes, fix) -> bool:
    """A fix counts only if it changes what is drawn."""
    before = json.dumps(visual(apply(b, changes), 'timekeeper'), sort_keys=True, default=str)
    after = json.dumps(visual(apply(b, {**changes, **fix}), 'timekeeper'), sort_keys=True, default=str)
    return before != after


def score(F) -> int:
    return sum(SEV[f['severity']] for f in F)


# ====================================================================== the loop
def run(studio, pid, task, scene, reason='produce'):
    """Job: produce one scene (up to max_rounds correction rounds). Records every version, then the pick."""
    st = studio.state(pid)
    cp = st['copilot']
    ctx = context(studio, pid, st)
    materialize(studio, pid, st)
    b = base(studio, pid, st, ctx, scene)
    bh = base_hash(b)
    have = cp['scenes'].get(scene, {}).get('versions', [])
    changes, versions = {}, []
    max_rounds = cp['settings'].get('max_rounds', 2)
    escalate = None
    for rnd in range(max_rounds + 1):
        sp = apply(b, changes)
        ih = _h([bh, changes])
        old = next((v for v in have if v['inputs_hash'] == ih), None)       # same inputs already drawn: reuse, never draw twice
        if old:
            v = old
        else:
            n = len(have) + len(versions) + 1
            drawn = draw(studio, pid, st, sp, studio.pdir(pid) / 'work' / 'scenes' / f'{scene}-v{n}')
            F = tech_checks(sp, drawn, ctx['research'])
            rev = ai.call(studio, pid, 'scene_review', {'scene': scene, 'technique': sp['technique'], 'params': sp['params'], 'theme': sp['theme'],
                                                         'banner': sp['banner'], 'stills': [str(studio.path(pid, s)) for s in drawn['stills']],
                                                         'changes_applied': [f'{k}:{v}' for k, v in changes.items()], 'line': sp['line'],
                                                         'tech_findings': [{k: f[k] for k in ('code', 'severity', 'detail')} for f in F]})
            for f in rev.get('findings', []):
                F.append({**_f(f.get('code', 'ART'), f.get('severity', 'minor'), f.get('detail', ''), f.get('detail_ar', ''), f.get('fix'), by='ai'),
                          'label': rev.get('label')})
            v = {'op': 'version', 'scene': scene, 'n': n, 'round': rnd, 'base_hash': bh, 'inputs_hash': ih, 'changes': changes,
                 'technique': sp['technique'], 'theme': sp['theme'], 'banner': sp['banner'], 'dur': sp['dur'], 'take': sp['take'],
                 'fallback': sp['fallback'], 'stills': drawn['stills'], 'times': drawn['times'], 'clip': drawn['clip'], 'clip_webm': drawn['clip_webm'],
                 'engine_scene': drawn['engine_scene'], 'findings': F, 'score': score(F), 'reviewer': rev.get('label'), 'reason': reason,
                 'status': 'ai_reviewed', 'params': sp['params'], 'line': sp['line']}
            studio.act(pid, 'cp_scene', v, actor='copilot')
            task.unit(scene=scene, round=rnd)
        versions.append(v)
        F = v['findings']
        fact = [f for f in F if f['code'] in ('YEAR_NOT_IN_RESEARCH', 'CLAIM_ON_SCREEN')]
        if fact:
            escalate = ('fact', fact[0]); break
        todo, unsafe, stuck = {}, None, []
        for f in F:
            if f['severity'] == 'info': continue
            bad = f['severity'] in ('critical', 'major')
            if not f.get('fix'):
                if bad: stuck.append(f)
                continue
            fx = {k: str(x) for k, x in f['fix'].items()}
            if set(fx) - SAFE_AI:
                unsafe = unsafe or f; continue                               # would touch something approved: ask
            new = {k: x for k, x in fx.items() if changes.get(k) != x}
            if new and _effective(b, changes, new): todo.update(new)
            elif bad: stuck.append(f)                                       # its fix is already in and it is still there
        if not todo:
            if unsafe: escalate = ('touches_approved', unsafe)
            elif stuck: escalate = ('retry_limit' if rnd else 'unfixable', stuck[0])
            break
        if rnd == max_rounds:
            escalate = ('retry_limit', next((f for f in F if f['severity'] in ('critical', 'major')), None)) \
                if any(f['severity'] in ('critical', 'major') for f in F) else None
            break
        changes = {**changes, **todo}
    best = min(versions, key=lambda v: (v['score'], -v['n']))
    left = [f for f in best['findings'] if f['severity'] != 'info']
    pick = {'op': 'pick', 'scene': scene, 'n': best['n'], 'base_hash': bh, 'rounds': len(versions) - 1,
            'status': 'needs_owner' if escalate else ('ai_reviewed_minor' if left else 'ai_reviewed'),
            'open': [{k: f.get(k) for k in ('code', 'severity', 'detail', 'detail_ar', 'by')} for f in left],
            'why': f'best of {len(versions)} version(s): {best["score"]} points of issues' if len(versions) > 1 else 'first version passed'}
    studio.act(pid, 'cp_scene', pick, actor='copilot')
    if escalate:
        kind, f = escalate
        title = {'fact': 'a factual problem on screen', 'touches_approved': 'a fix would change something you approved',
                 'unfixable': 'a problem the Co-Pilot cannot fix safely', 'retry_limit': f'still not right after {len(versions) - 1} correction round(s)'}[kind]
        opts = {'fact': ['remove_banner', 'manual'], 'touches_approved': ['accept_best', 'retry_with_change', 'manual'],
                'unfixable': ['accept_best', 'retry_with_change', 'manual'], 'retry_limit': ['accept_best', 'retry_with_change', 'manual']}[kind]
        studio.act(pid, 'cp_exception', {'id': f'ex-{scene}-{best["n"]}', 'kind': kind, 'scene': scene, 'version': best['n'], 'title': f'Scene {scene}: {title}',
                                         'detail': (f or {}).get('detail', ''), 'detail_ar': (f or {}).get('detail_ar', ''), 'options': opts,
                                         'evidence': best['stills'][1:3], 'pause': True}, actor='copilot')
    return {'scene': scene, 'pick': best['n'], 'versions': len(versions), 'escalated': escalate and escalate[0]}
