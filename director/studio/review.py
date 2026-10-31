"""Independent review of a rendered draft: what was actually rendered, never what was intended.

It reads the MP4, the engine storyboard that produced it and the research file, and writes findings with a scene,
a timecode, an evidence still, a severity and a recommended correction. It never edits art, takes or the storyboard:
accepting a finding only creates a correction task (store.a_finding_decision); dismissing keeps it in the history.

Checks (each one names the perspective it stands for):
  technical_qa       size/length/black/frozen/static opening/loudness/palette (director/art/review.technical_pass)
  technical_qa       layout: the engine's own --check (cut by the frame, print over print, on the captions, faces)
  technical_qa       audio/video sync: the voice onset in each scene against where the storyboard put it
  historical_product years and claims on screen against the research file; drawn watches presented as a brand
  historical_product placeholders where a real photo is still missing
  arabic_readability caption groups, banner length, Latin in captions, digits style
  motion_director    scenes whose camera moves less than 3 % (director/studio/motion.py)
  art_director       themes outside the brand's palette (style consistency)
"""
from __future__ import annotations
import json, re, subprocess
from pathlib import Path

import numpy as np

from ..art import review as R
from . import checks, engine, motion
from .storyboard import VOICE_AT

YEAR = re.compile(r'(1[89]\d\d|20\d\d)')


def _still(video, t, out):
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{max(0, t):.2f}', '-i', str(video), '-frames:v', '1', '-vf', 'scale=360:-2', str(out)], check=True)
    return out


def _pcm(path, sr=8000):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-ac', '1', '-ar', str(sr), '-f', 'f32le', '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


def _voice_offsets(video, scenes, work: Path, sr=8000):
    """Where each scene's own voice clip actually sits in the rendered audio: cross-correlate the first 2.5 s of the
    clip with the film's audio around the scene start. Paper sounds and music do not fool it (an energy onset was
    fooled by the transition sounds). Returns {scene: seconds after the scene start, correlation strength}."""
    film = _pcm(video, sr)
    out = {}
    for s in scenes:
        if not s.get('voice'): continue
        clip_f = work / s['voice']
        if not clip_f.exists(): continue
        clip = _pcm(clip_f, sr)[:int(2.5 * sr)]
        if len(clip) < sr // 2: continue
        a0 = max(0, int((s['start'] - 0.5) * sr)); a1 = min(len(film), int((s['start'] + 3.5) * sr) + len(clip))
        seg = film[a0:a1]
        if len(seg) <= len(clip): continue
        c = clip - clip.mean(); n = len(c)
        corr = np.correlate(seg - seg.mean(), c, mode='valid')
        energy = np.sqrt(np.convolve((seg - seg.mean()) ** 2, np.ones(n), mode='valid')) * np.linalg.norm(c) + 1e-9
        norm = corr / energy
        k = int(np.argmax(norm))
        out[s['id']] = (round((a0 + k) / sr - s['start'], 3), round(float(norm[k]), 3))
    return out


def _text_box(e):
    if e.get('type') not in ('text', 'stamp') or not isinstance(e.get('x'), (int, float)) or not isinstance(e.get('y'), (int, float)):
        return None
    size = e.get('size', 90 if e['type'] == 'text' else 120); n = len(str(e.get('text', '')))
    w = min(e.get('w') or 9e9, n * size * (0.52 if e['type'] == 'text' else 0.62) + (0 if e['type'] == 'text' else size * 0.6))
    h = size * (1.25 if e['type'] == 'text' else 1.5)
    return (e['x'] - w / 2, e['y'] - h / 2, e['x'] + w / 2, e['y'] + h / 2)


def _text_overlaps(scenes):
    """A stamp or a line of text drawn over another line of text (estimated boxes; the engine check covers prints)."""
    out = []
    for s in scenes:
        boxes = [(e, _text_box(e)) for e in s['src'].get('elements', [])]
        boxes = [(e, b) for e, b in boxes if b]
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                (e1, a), (e2, b) = boxes[i], boxes[j]
                ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
                small = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
                if small and ix * iy / small > 0.10:
                    out.append((s, e1, e2, round(100 * ix * iy / small)))
    return out


def _frame_geometry(scenes):
    """Cards, prints and text whose box leaves the 720-wide frame (the engine's own check covers prints only)."""
    out = []
    for s in scenes:
        for e in s['src'].get('elements', []):
            if e.get('type') not in ('card', 'photo', 'image', 'text', 'sticky') or e.get('crop'): continue
            x, w = e.get('x'), e.get('w')
            if not isinstance(x, (int, float)) or not isinstance(w, (int, float)) or w >= 700: continue
            l, r = x - w / 2, x + w / 2
            out_px = max(0, -l) + max(0, r - 720)
            if out_px > 0.12 * w:
                out.append((s, e, round(100 * out_px / w)))
    return out


def run(studio, pid, task, render_id, profile, other_profiles, research, platform='reels', label='draft'):
    st = studio.state(pid)
    r = next(x for x in st['renders'] if x['id'] == render_id)
    video = studio.path(pid, r['file'])
    esb = studio.read_json(pid, r['engine_storyboard'])
    out_dir = studio.pdir(pid) / 'work' / f'review-{render_id}-{len(st["review"]["runs"]) + 1}'
    # scene times as rendered (from the engine storyboard, with the end card)
    t, scenes = 0.0, []
    for s in esb['scenes']:
        scenes.append({'id': s.get('id') or ('endcard' if s.get('endcard') else f'sc{len(scenes)}'), 'start': round(t, 3),
                       'dur': s['dur'], 'end': round(t + s['dur'], 3), 'voice': s.get('voice'), 'voiceAt': s.get('voiceAt', .15), 'src': s})
        t += s['dur']
    pack = R.build_pack(video, out_dir, {'scenes': [{'id': s['id'], 'start': s['start'], 'end': s['end']} for s in scenes]})
    task.unit(what='evidence pack')
    F = []

    def add(code, sev, persp, detail, rec, scene=None, t=None, fix_stage='art'):
        F.append({'code': code, 'severity': sev, 'perspective': persp, 'detail': detail, 'recommendation': rec,
                  'scene': scene, 't': None if t is None else round(t, 2), 'fix_stage': fix_stage})

    # 1. technical pass from the existing Art Reviewer
    for f in R.technical_pass(pack, platform, profile, other_profiles):
        if f['code'] == 'BLACK_STRETCH' and str(f['scene'] or '').startswith('endcard'):
            continue                       # the Time Keeper end card opens on its near-black plate by design
        add(f['code'], f['severity'], f['perspective'], f['detail'], f['suggestion'] or 'fix and re-render', f['scene'], f['t'],
            'draft' if f['code'] in ('WRONG_SIZE', 'LOUDNESS', 'TRUE_PEAK', 'TOO_LONG') else 'art')
    task.unit(what='technical pass')
    # 2. layout (the engine's own check, read from the render's storyboard)
    for line in engine.check(esb, studio.pdir(pid) / r.get('work', f'work/render-{render_id}')):
        m = re.match(r'\s*scene (\d+)\s+([\d.]+)-([\d.]+)s\s+(.*)', line)
        if not m: continue
        k, t0, t1, what = int(m.group(1)) - 1, float(m.group(2)), float(m.group(3)), m.group(4)
        sc = scenes[k] if 0 <= k < len(scenes) else None
        tt = t0 if sc is None or t0 >= sc['start'] else sc['start'] + t0          # the engine reports film time
        code = ('CUT_BY_FRAME' if 'outside the frame' in what else 'ON_CAPTIONS' if 'on the captions' in what else
                'UNDER_BANNER' if 'under the banner' in what else 'FACE_COVERED' if 'of the head of' in what else 'OVERLAP')
        rec = {'CUT_BY_FRAME': 'bring it inside the frame or mark a deliberate crop',
               'ON_CAPTIONS': 'move it above the caption band (y 960-1070)', 'UNDER_BANNER': 'lower it below the banner',
               'FACE_COVERED': 'move the element off the face', 'OVERLAP': 'separate the prints or mark a deliberate stack'}[code]
        add(code, 'major', 'technical_qa', f'{what} ({t0:.1f}-{t1:.1f} s)', rec, sc and sc['id'], tt)
    task.unit(what='layout check')
    # 3. audio/video sync
    offs = _voice_offsets(video, scenes, studio.pdir(pid) / r.get('work', f'work/render-{render_id}'))
    for s in scenes:
        s['voiceAt'] = VOICE_AT                 # where the studio always puts the voice (captions are timed from there)
        if not s.get('voice'): continue
        o = offs.get(s['id'])
        if o is None or o[1] < 0.3:
            add('VOICE_MISSING', 'critical', 'technical_qa', 'the scene\'s voice clip could not be found in the film audio',
                'check the clip and the mix', s['id'], s['start'], 'voice')
        elif abs(o[0] - VOICE_AT) > 0.12:
            d = o[0] - VOICE_AT
            add('AV_SYNC', 'critical' if abs(d) > 0.4 else 'major', 'technical_qa',
                f"voice starts {o[0]:.2f} s into the scene; captions and visuals expect {VOICE_AT:.2f} s ({d:+.2f} s, match {o[1]})",
                'realign the voice clip with its scene and re-render', s['id'], s['start'] + o[0], 'draft')
    prev_banner = None
    for s in scenes:                         # a missing banner key keeps the previous scene's banner on screen
        if 'banner' not in s['src'] and prev_banner:
            add('BANNER_CARRIED_OVER', 'major', 'arabic_readability', f"the banner «{prev_banner}» from the previous scene stays on screen here",
                'give the scene its own banner or an explicit empty one', s['id'], s['start'] + 0.5)
        prev_banner = s['src'].get('banner') if 'banner' in s['src'] else prev_banner
    for s, e1, e2, pct in _text_overlaps(scenes):
        add('TEXT_OVERLAP', 'major', 'art_director', f"{e1['type']} «{str(e1.get('text'))[:24]}» and {e2['type']} «{str(e2.get('text'))[:24]}» overlap (~{pct}%)",
            'move one of them so both read cleanly', s['id'], s['start'] + max((e.get('in') or {}).get('at', 0) for e in (e1, e2)) + 0.5)
    for s, e, pct in _frame_geometry(scenes):
        add('CUT_BY_FRAME', 'major', 'technical_qa', f"{e['type']} «{str(e.get('title') or e.get('text') or e.get('label') or '')[:30]}» is {pct}% outside the frame",
            'bring it inside the frame or mark a deliberate crop', s['id'], s['start'] + 1.0)
    task.unit(what='sync')
    # 4. history and watch design
    rtext = json.dumps(research or {}, ensure_ascii=False)
    years = set(YEAR.findall(rtext))
    for s in scenes:
        texts = [s['src'].get('banner') or ''] + [e.get('text', '') or e.get('title', '') or e.get('label', '') for e in s['src'].get('elements', [])]
        for tx in texts:
            for y in YEAR.findall(str(tx)):
                if y not in years:
                    add('YEAR_NOT_IN_RESEARCH', 'critical', 'historical_product', f'«{tx}» shows {y}, which the research file does not support',
                        'correct the year or add a sourced claim', s['id'], s['start'] + 0.5, 'art')
        for c in checks.check_version([{'id': s['id'], 'text': ' '.join(map(str, texts))}], research, []):
            if c['code'] == 'CLAIM_UNSUPPORTED':
                add('CLAIM_ON_SCREEN', 'critical', 'historical_product', c['detail'], 'remove or attribute the claim', s['id'], s['start'] + 0.5, 'art')
        for e in s['src'].get('elements', []):
            if e.get('type') == 'watch' and re.search(r'rolex|رولكس|oyster|أويستر', str(e.get('brand', '')) + str(e.get('label', '')), re.I):
                add('DRAWN_BRAND_WATCH', 'critical', 'historical_product', 'a drawn watch is labelled as the real brand: its parts are not the real ones',
                    'use a licensed photograph of the real watch, or remove the brand label', s['id'], s['start'] + 0.5, 'art')
            if e.get('type') == 'sketch' and e.get('technical') and not any('توضيحي' in str(x.get('text', '')) for x in s['src']['elements']):
                add('DRAWING_UNLABELLED', 'major', 'historical_product', 'a technical drawing without the "simplified principle" label',
                    'add the label so it is not read as the maker\'s engineering drawing', s['id'], s['start'] + 0.5, 'art')
                break
            if e.get('asset') and not e.get('src') and not (studio.pdir(pid) / 'assets').glob(e['asset'] + '.*'):
                pass
        for e in s['src'].get('elements', []):
            if e.get('silhouette'):
                add('PLACEHOLDER_PERSON', 'major', 'historical_product', f"a labelled placeholder stands in for {e.get('label') or 'a real person'} (no documented photo in the project)",
                    'add a licensed, documented photograph or keep the person off screen', s['id'], s['start'] + 1.0)
            if e.get('asset') and not any((studio.pdir(pid) / 'assets').glob(e['asset'] + '.*')):
                add('MISSING_ASSET', 'major', 'historical_product', f"REAL PHOTO NEEDED: {e['asset']} ({e.get('desc', '')})",
                    'add the licensed photograph to the project, or use another approved concept', s['id'], s['start'] + 1.0, 'art')
    task.unit(what='history')
    # 5. readability, pacing, style
    themes = set(profile.get('look', {}).get('themes', [])) | {'tk-bone', 'tk-linen', 'tk-graphite', 'tk-ink', 'tk-black'}
    brand_bgs = [t['bg'] for t in esb.get('themes', {}).values()] + list(profile.get('look', {}).get('palette', {}).values())
    for s in scenes:
        b = s['src'].get('banner')
        if b and len(b.split()) > 6:
            add('BANNER_LONG', 'minor', 'arabic_readability', f'banner has {len(b.split())} words (6 or fewer)', 'shorten the banner', s['id'], s['start'] + .3)
        cap = ' '.join(w for _, w in s['src'].get('words', [])) or s['src'].get('captions', '')
        if re.search('[A-Za-z]', cap):
            add('LATIN_IN_CAPTIONS', 'minor', 'arabic_readability', 'Latin letters in the Arabic captions', 'write the Arabic form', s['id'], s['start'] + .5)
        th = s['src'].get('theme')
        if isinstance(th, dict) and th.get('bg', '').upper() not in {c.upper() for c in brand_bgs}:
            add('OFF_BRAND_THEME', 'major', 'art_director', f"background {th.get('bg')} is not a {profile['id']} colour", 'use a brand theme', s['id'], s['start'] + .3)
        if isinstance(th, str) and th not in themes:
            add('OFF_BRAND_THEME', 'major', 'art_director', f"theme {s['src']['theme']} is not a {profile['id']} theme", 'use a brand theme', s['id'], s['start'] + .3)
        cam = motion.amount(s['src'], s['dur'])               # a camera key is not a move: it has to travel at least 3 %
        if cam + motion.TOL < motion.MIN and not s['src'].get('endcard'):
            add('LONG_HOLD', 'minor' if s['dur'] <= 8 else 'major', 'motion_director',
                f"{s['dur']:.1f} s with the camera moving {cam * 100:.1f} % (at least {motion.MIN * 100:.0f} %)",
                'a 3-5 % push, drift or dolly, and a punch-in on a word if the scene is long', s['id'], s['start'] + s['dur'] / 2)
    task.unit(what='readability')
    # evidence: one still per finding at its timecode
    for i, f in enumerate(F):
        f['id'] = f"{render_id}-{label}-{i + 1:02d}"
        tt = f['t'] if f['t'] is not None else 0.5
        f['evidence'] = studio.put_file(pid, _still(video, tt, out_dir / 'ev' / f"{f['id']}.jpg"), 'jpg')
    task.unit(what='evidence')
    rec = {'id': f'rv-{render_id}-{label}', 'render': render_id, 'label': label, 'platform': platform, 'findings': F,
           'contact': studio.put_file(pid, out_dir / 'contact.jpg', 'jpg'), 'scenes': len(scenes),
           'counts': {s: sum(1 for f in F if f['severity'] == s) for s in ('critical', 'major', 'minor', 'info')}}
    studio.act(pid, 'review', rec, actor='reviewer')
    return {'review': rec['id'], 'findings': len(F)}
