"""Art Reviewer: evaluates what was actually rendered, never the Director's intentions.

Read-only by design: it opens the video (and an optional timeline) for reading, and writes only into its own
evidence folder. It does not import the Art Director, the voice modules or the paid gateway (a test enforces it).

  build_pack(video, out_dir, timeline=None)   -> evidence pack: stills at scene start/mid/end, a 12-frame motion
                                                 strip per scene, a contact sheet, measured facts
  technical_pass(pack, platform, profiles)    -> deterministic findings (dimensions, length, black and frozen
                                                 stretches, a static opening on hook-first platforms, loudness,
                                                 dominant colours that belong to another project's identity)
  review_packet(pack, stage, profile, facts)  -> the questions each perspective must answer, tied to evidence
  finding(...)                                 -> validated finding record
"""
from __future__ import annotations
import json, re, shutil, subprocess, tempfile
from pathlib import Path

SEVERITIES = ('critical', 'major', 'minor', 'info')
STAGES = ('concept', 'scene', 'final')
PERSPECTIVES = ('art_director', 'motion_director', 'historical_product', 'arabic_readability', 'technical_qa')
PLATFORMS = {
    'tiktok': {'size': (1080, 1920), 'max_s': 600, 'hook_moves': True, 'lufs': -14},
    'reels': {'size': (1080, 1920), 'max_s': 180, 'hook_moves': True, 'lufs': -14},
    'shorts': {'size': (1080, 1920), 'max_s': 180, 'hook_moves': True, 'lufs': -14},
    'youtube': {'size': (1920, 1080), 'max_s': None, 'hook_moves': False, 'lufs': -14},
    'whatsapp': {'size': None, 'max_s': None, 'hook_moves': False, 'lufs': -16},
}


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def probe(video) -> dict:
    r = _run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration:stream=codec_type,width,height,r_frame_rate',
              '-of', 'json', str(video)])
    d = json.loads(r.stdout)
    v = next(s for s in d['streams'] if s['codec_type'] == 'video')
    num, den = v['r_frame_rate'].split('/')
    return {'duration': float(d['format']['duration']), 'width': v['width'], 'height': v['height'],
            'fps': round(float(num) / float(den), 3), 'audio': any(s['codec_type'] == 'audio' for s in d['streams'])}


def _still(video, t, out):
    _run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t:.3f}', '-i', str(video), '-frames:v', '1', '-vf', 'scale=360:-2', str(out)])
    return out


def _strip(video, t0, t1, out, n=12):
    fps = n / max(0.1, t1 - t0)
    _run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t0:.3f}', '-t', f'{t1 - t0:.3f}', '-i', str(video),
          '-vf', f'fps={fps:.4f},scale=180:-2,tile={n}x1', '-frames:v', '1', str(out)])
    return out


def build_pack(video, out_dir, timeline: dict | None = None, every=4.0) -> dict:
    video, out = Path(video), Path(out_dir)
    (out / 'stills').mkdir(parents=True, exist_ok=True); (out / 'strips').mkdir(exist_ok=True)
    meta = probe(video)
    scenes = []
    if timeline and timeline.get('scenes'):
        for s in timeline['scenes']:
            st, en = float(s['start']), float(s.get('end', s['start'] + s.get('duration', 0)))
            scenes.append({'id': s['id'], 'start': st, 'end': min(en, meta['duration'])})
    else:
        t = 0.0
        while t < meta['duration']:
            scenes.append({'id': f'seg{int(t):04d}', 'start': t, 'end': min(t + every, meta['duration'])}); t += every
    for s in scenes:
        s['stills'] = {}
        for label, t in (('start', s['start'] + 0.15), ('mid', (s['start'] + s['end']) / 2), ('end', max(s['start'], s['end'] - 0.15))):
            p = out / 'stills' / f"{s['id']}_{label}.jpg"
            s['stills'][label] = str(_still(video, t, p).relative_to(out))
        mid = (s['start'] + s['end']) / 2
        s['strip'] = str(_strip(video, max(s['start'], mid - 1.5), min(s['end'], mid + 1.5), out / 'strips' / f"{s['id']}.jpg").relative_to(out))
    sheet = out / 'contact.jpg'                     # one tile per scene (its middle still), in scene order
    with tempfile.TemporaryDirectory() as td:
        for i, s in enumerate(scenes[:96]):
            shutil.copyfile(out / s['stills']['mid'], Path(td) / f'{i:04d}.jpg')
        n = min(len(scenes), 96)
        _run(['ffmpeg', '-v', 'error', '-y', '-framerate', '1', '-i', str(Path(td) / '%04d.jpg'), '-vf',
              f"scale=180:-2,setsar=1,tile=8x{(n + 7) // 8}:padding=4:color=0x202020", '-frames:v', '1', str(sheet)])
    pack = {'video': str(video), 'meta': meta, 'scenes': scenes, 'contact': 'contact.jpg',
            'measured': measure(video, meta)}
    (out / 'pack.json').write_text(json.dumps(pack, ensure_ascii=False, indent=1), encoding='utf-8')
    return pack


def measure(video, meta) -> dict:
    """Black and frozen stretches, loudness, and per-second dominant colours (all read-only ffmpeg filters)."""
    r = _run(['ffmpeg', '-v', 'info', '-nostats', '-i', str(video), '-vf', 'blackdetect=d=0.3:pix_th=0.08,freezedetect=n=0.003:d=1.0',
              '-an', '-f', 'null', '-'])
    black = [(float(a), float(b)) for a, b in re.findall(r'black_start:([\d.]+) black_end:([\d.]+)', r.stderr)]
    fs = [float(x) for x in re.findall(r'freeze_start: ([\d.]+)', r.stderr)]
    fe = [float(x) for x in re.findall(r'freeze_end: ([\d.]+)', r.stderr)]
    frozen = [(s, fe[i] if i < len(fe) else meta['duration']) for i, s in enumerate(fs)]
    loud = {}
    if meta['audio']:
        a = _run(['ffmpeg', '-v', 'info', '-nostats', '-i', str(video), '-af', 'ebur128=peak=true', '-f', 'null', '-'])
        m = re.findall(r'I:\s+(-?[\d.]+) LUFS', a.stderr); p = re.findall(r'Peak:\s+(-?[\d.]+) dBFS', a.stderr)
        loud = {'integrated_lufs': float(m[-1]) if m else None, 'true_peak_dbfs': float(p[-1]) if p else None}
    data = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(video), '-vf', 'fps=1,scale=16:28', '-f', 'rawvideo',
                           '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
    per = 16 * 28 * 3
    dominant = []
    for i in range(len(data) // per):
        px = data[i * per:(i + 1) * per]
        counts = {}
        for j in range(0, per, 3):
            q = (px[j] // 16, px[j + 1] // 16, px[j + 2] // 16)
            counts[q] = counts.get(q, 0) + 1
        q, c = max(counts.items(), key=lambda kv: kv[1])
        dominant.append({'t': i, 'rgb': [v * 16 + 8 for v in q], 'share': round(c / (per // 3), 3)})
    return {'black': black, 'frozen': frozen, 'loudness': loud, 'dominant': dominant}


def _hex(h):
    h = h.lstrip('#'); return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def _dist(a, b):
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def finding(code, severity, detail, stage='final', perspective='technical_qa', scene=None, t=None, evidence=None,
            suggestion='', status='open') -> dict:
    assert severity in SEVERITIES and stage in STAGES and perspective in PERSPECTIVES, (severity, stage, perspective)
    return {'code': code, 'severity': severity, 'stage': stage, 'perspective': perspective, 'scene': scene,
            't': None if t is None else round(t, 2), 'evidence': evidence, 'detail': detail,
            'suggestion': suggestion, 'status': status}


def _scene_at(pack, t):
    for s in pack['scenes']:
        if s['start'] <= t < s['end']:
            return s
    return None


def technical_pass(pack: dict, platform: str, own_profile: dict, other_profiles: list[dict]) -> list[dict]:
    m, meas, P, out = pack['meta'], pack['measured'], PLATFORMS[platform], []
    if P['size'] and (m['width'], m['height']) != P['size']:
        out.append(finding('WRONG_SIZE', 'critical', f"{m['width']}x{m['height']}, {platform} needs {P['size'][0]}x{P['size'][1]}"))
    if P['max_s'] and m['duration'] > P['max_s']:
        out.append(finding('TOO_LONG', 'critical', f"{m['duration']:.0f} s, {platform} limit {P['max_s']} s"))
    for a, b in meas['black']:
        if b < m['duration'] - 0.3:                        # black that runs to the very end is the intended close (e.g. the TK end card)
            s = _scene_at(pack, a)
            out.append(finding('BLACK_STRETCH', 'major', f'black from {a:.2f} to {b:.2f} s', scene=s and s['id'], t=a,
                               evidence=s and s['stills']['start'], suggestion='check a missing layer or a transition gap'))
    for a, b in meas['frozen']:
        s = _scene_at(pack, a)
        if P['hook_moves'] and a < 0.1 and b > 0.8:
            out.append(finding('STATIC_OPENING', 'major', f'the first {b:.1f} s do not move; {platform} needs a moving hook from frame 1',
                               scene=s and s['id'], t=0, evidence=s and s['stills']['start'],
                               suggestion='start on the hook; export the cover as a separate image'))
        elif b - a >= 3.0:
            out.append(finding('STATIC_STRETCH', 'minor', f'nothing moves for {b - a:.1f} s ({a:.1f}–{b:.1f})',
                               perspective='motion_director', scene=s and s['id'], t=a, evidence=s and s['strip'],
                               suggestion='add a camera drift or a layer change unless the stillness is intended'))
    L = meas['loudness']
    if L.get('integrated_lufs') is not None and abs(L['integrated_lufs'] - P['lufs']) > 2:
        out.append(finding('LOUDNESS', 'minor', f"{L['integrated_lufs']} LUFS, target {P['lufs']}"))
    if L.get('true_peak_dbfs') is not None and L['true_peak_dbfs'] > -1.0:
        out.append(finding('TRUE_PEAK', 'major', f"true peak {L['true_peak_dbfs']} dBFS (> -1)"))
    own = [_hex(c) for c in own_profile['look']['palette'].values()]
    for other in other_profiles:
        if other['id'] == own_profile['id']:
            continue
        theirs = [_hex(c) for c in other['look']['palette'].values()]
        hits = [d for d in meas['dominant'] if d['share'] > 0.35 and
                min(_dist(d['rgb'], c) for c in theirs) < 24 and min(_dist(d['rgb'], c) for c in own) > 24]
        if len(hits) >= max(3, len(meas['dominant']) // 10):
            out.append(finding('PALETTE_CONTAMINATION', 'major',
                               f"{len(hits)} seconds are dominated by {other['id']} colours", perspective='art_director',
                               t=hits[0]['t'], suggestion=f"use the {own_profile['id']} palette"))
    return out


QUESTIONS = {
    'concept': {
        'art_director': ['Does each proposed visual illustrate its narration line?', 'Is the chosen technique the best of the options offered, and why?',
                         'Does it match the approved profile (palette, type, motifs)? Anything from another project?'],
        'historical_product': ['Is every person, object and place the real one, with a verified source and licence?',
                               'Is anything shown that the facts file does not support?'],
    },
    'scene': {
        'art_director': ['Composition: one clear focal point? hierarchy readable on a phone?', 'Proportions of people and products consistent with other scenes?'],
        'motion_director': ['Does something change every 2–3 s? Any unintended static stretch (see strip)?', 'Camera moves smooth, with the right timing to the words?'],
        'historical_product': ['Correct watch, reference number, person, year and place on every label?', 'Sources and licences recorded for every image?'],
        'arabic_readability': ['Captions and labels readable, correctly shaped, ≤ 3 words per group, not covering faces?', 'Western digits; no clipped text?'],
        'technical_qa': ['Nothing clipped, overlapping unintentionally, or inside the platform safe zones?'],
    },
    'final': {
        'art_director': ['Consistent art direction across scenes; no abrupt changes of character, scale, light or colour?', 'Strong opening and closing frames?'],
        'motion_director': ['Pacing and transitions; no repetitive or static stretches without purpose?', 'Narration and visuals in sync?'],
        'historical_product': ['Every factual image still correct after the final edit?'],
        'arabic_readability': ['All on-screen Arabic correct and readable at phone size?'],
        'technical_qa': ['Platform size, length, safe zones, loudness and export integrity?'],
    },
}


def review_packet(pack: dict, stage: str, profile: dict, facts: list | None = None) -> dict:
    """What each perspective must answer, with the evidence it must look at (stills and strips, not prompts)."""
    return {'stage': stage, 'profile': {'id': profile['id'], 'version': profile.get('version')},
            'evidence': {'contact': pack['contact'], 'scenes': [{k: s[k] for k in ('id', 'start', 'end', 'stills', 'strip')}
                                                                 for s in pack['scenes']]},
            'facts': facts or [], 'questions': QUESTIONS[stage],
            'finding_schema': ['code', 'severity', 'stage', 'perspective', 'scene', 't', 'evidence', 'detail', 'suggestion', 'status']}
