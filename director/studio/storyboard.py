"""Storyboard and draft render.

build(): approved script + selected hook + draft takes + art → one scene per narration line, then the brand's end card.
  * Each scene's length follows its take (voice starts 0.15 s in, 0.45 s tail); captions use the take's word times.
  * Art: the scene's APPROVED concept version if there is one; otherwise the brief's default technique, and the
    scene is marked 'art not approved'. A take that is not approved is used and marked 'voice not approved'.
    So a draft can always be built, and it always says what in it is not yet approved.
render(): the free local engine (paper-story) draws 1080x1920 frames and mixes the per-scene voice clips; the end
  card is Time Keeper's own (gold hand draws the logo, two ticks, black). Output: an MP4 marked DRAFT.
"""
from __future__ import annotations
import importlib.util, json, shutil, subprocess, time
from pathlib import Path

from . import art, engine
from .voice import approved_script
from .checks import words as checks_words

ROOT = Path(__file__).resolve().parents[2]
VOICE_AT, TAIL = 0.15, 0.45
NARRATOR_PACE = {'timekeeper': (1.74, 'median speaking rate of the 30 approved Royal Oak takes (ElevenLabs, Abdullah)')}
TRANSITION = {'l9': 'fade', 'l12': 'fade', 'l13': 'fade'}


def _endcard(sb_dir: Path, theme='tk-black'):
    spec = importlib.util.spec_from_file_location('tk_endcard', engine.ENGINE / 'tk_endcard.py')
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    logo = sb_dir / 'tk-logo-512.png'
    if not logo.exists(): shutil.copyfile(engine.ENGINE / 'tk-logo-512.png', logo)
    m.LOGO = str(logo)
    return m.endcard(str(sb_dir), theme)


def build(studio, pid) -> dict:
    from .store import Refused
    st = studio.state(pid)
    sv = approved_script(st)
    if sv is None:
        raise Refused('approve a script version first')
    brief = art.brief_for(studio, pid, st)
    hook = next((o for o in st['hooks']['options'] if o['id'] == st['hooks']['selected']), None)
    lines = studio.read_json(pid, sv['file'])['lines']
    scenes, warnings, t = [], [], 0.0
    for ln in lines:
        sid = ln['id']
        b = brief['scenes'].get(sid) or brief['scenes'].get('h' if ln.get('role') == 'hook' else sid)
        if b is None:
            raise Refused(f'the art brief has no scene for line {sid}')
        vl = (st['voice'].get('lines') or {}).get(sid, {})
        take = st['voice']['takes'].get(vl.get('take')) if vl.get('take') else None     # only a take of THIS text
        appr = st['art']['approved'].get(sid if sid in brief['scenes'] else 'h')
        if appr:
            c = st['art']['concepts'][appr['concept']]
            ver = next(v for v in c['versions'] if v['v'] == appr['version'])
            tech, params, theme, art_status = c['technique'], ver.get('params', c['params']), ver.get('theme', c['theme']), 'approved'
        else:
            tech = b['default']; params = b['concepts'][tech]; theme = params.get('theme', b.get('theme', 'tk-bone'))
            art_status = 'not reviewed (brief default)'
        dur = round(VOICE_AT + take['seconds'] + TAIL, 2) if take else b.get('dur', 5.0)
        banner = None if ln.get('role') == 'hook' else b.get('banner')        # the hook visual itself carries the on-screen text in frame 1
        status = {'voice': ('approved' if take and take['status'] == 'approved' else 'not approved' if take else
                            'stale: the script changed after it was voiced' if vl.get('status') == 'stale' else 'missing'),
                  'art': art_status}
        if tech in ('neutral_placeholder',) or art.missing_assets(tech, params, studio.pdir(pid) / 'assets'):
            status['art'] += ' · PLACEHOLDER (real photo needed)'
        if status['voice'] != 'approved': warnings.append(f'{sid}: voice {status["voice"]}')
        if status['art'] != 'approved': warnings.append(f'{sid}: art {status["art"]}')
        scenes.append({'id': sid, 'line': ln['text'], 'start': round(t, 2), 'dur': dur, 'technique': tech, 'theme': theme,
                       'params': params, 'banner': banner, 'take': take['id'] if take else None, 'status': status,
                       'transition': TRANSITION.get(sid, 'cut' if scenes else 'none'),
                       'concept': appr and appr['concept'], 'art_version': appr and appr['version']})
        t += dur
    seconds = round(t + 4.5 + 1.3, 2)
    # what the FINAL narration would take: words at the brand narrator's measured pace, same pauses and end card
    n_words = sum(len(checks_words(s['line'])) for s in scenes)
    rate, rate_src = NARRATOR_PACE.get(st['brand'], (None, None))
    est = round(n_words / rate + len(scenes) * (VOICE_AT + TAIL + 0.15) + 5.8, 1) if rate else None
    doc = {'v': len(st['storyboards']) + 1, 'script_v': sv['v'], 'hook': hook and hook['id'], 'scenes': scenes,
           'endcard': 'timekeeper' if st['brand'] == 'timekeeper' else None}
    rel = studio.put(pid, json.dumps(doc, ensure_ascii=False, indent=1).encode(), 'json')
    rec = {'v': doc['v'], 'file': rel, 'script_v': sv['v'], 'hook': doc['hook'], 'seconds': seconds, 'warnings': warnings,
           'words': n_words, 'est_final_seconds': est, 'pace': {'words_per_s': rate, 'source': rate_src},
           'scenes': [{k: s[k] for k in ('id', 'start', 'dur', 'technique', 'take', 'status', 'transition', 'banner', 'concept', 'art_version')} for s in scenes]}
    studio.act(pid, 'storyboard', rec, actor='system')
    return rec


def engine_storyboard(studio, pid, doc: dict, work: Path) -> dict:
    """The engine's storyboard JSON for a studio storyboard, with its files copied into `work`."""
    st = studio.state(pid)
    work.mkdir(parents=True, exist_ok=True)
    (work / 'voice').mkdir(exist_ok=True)
    adir = studio.pdir(pid) / 'assets'
    if adir.exists():
        (work / 'assets').mkdir(exist_ok=True)
        for f in adir.glob('*'): shutil.copyfile(f, work / 'assets' / f.name)
    scenes = []
    for s in doc['scenes']:
        sc = art.scene_visual(s['technique'], s['params'], s['theme'], s['dur'], s['banner'])
        sc.update({'id': s['id'], 'dur': s['dur'], 'transition': s['transition'] if s['transition'] != 'none' else 'cut',
                   'status': 'METAPHOR' if s['technique'] in ('kinetic_type', 'paper_cut', 'parallax_25d') else 'CONFIRMED'})
        if s['take']:
            take = st['voice']['takes'][s['take']]
            src = studio.path(pid, take['wav'])
            dst = work / 'voice' / f"{s['id']}.wav"
            if not src.exists():
                raise FileNotFoundError(f"voice file for {s['id']} is missing: {take['wav']}")
            shutil.copyfile(src, dst)
            sc['voice'] = f"voice/{s['id']}.wav"; sc['voiceAt'] = VOICE_AT
            sc['words'] = [[round(VOICE_AT + w['s'], 2), w['w']] for w in take['words']]
        else:
            sc['captions'] = s['line']
        scenes.append(sc)
    if doc.get('endcard') == 'timekeeper':
        for sc in _endcard(work, 'tk-black'):
            sc.setdefault('banner', None)      # no banner from the last scene on the logo card
            scenes.append(sc)
    return {'width': 720, 'height': 1280, 'fps': 30, 'dir': 'rtl', **art.style('timekeeper'), 'scenes': scenes}


def render(studio, pid, task, storyboard_v=None, scale=1.5, inject=None):
    """Job: draw the draft film. `inject` is only used by the UAT defect copy (never on the project's own render)."""
    st = studio.state(pid)
    sbrec = next(s for s in st['storyboards'] if s['v'] == (storyboard_v or st['storyboards'][-1]['v']))
    doc = studio.read_json(pid, sbrec['file'])
    rid = f"r{len(st['renders']) + 1}"
    work = studio.pdir(pid) / 'work' / f'render-{rid}'
    studio.act(pid, 'render', {'id': rid, 'state': 'running', 'storyboard_v': sbrec['v']}, actor='system')
    try:
        esb = engine_storyboard(studio, pid, doc, work)
        if inject: esb = inject(esb, work)
        sbp = work / 'storyboard.json'; sbp.write_text(json.dumps(esb, ensure_ascii=False), encoding='utf-8')
        task.unit(what='storyboard')
        chk = engine.check(esb, work)
        task.unit(what='layout check')
        out = work / 'draft.mp4'
        t0 = time.monotonic()
        with studio.log.task(pid, 'draft frames (10 % steps)', 10, stage='draft', actor='system') as ft:   # equal units: a real ETA
            log = engine.video(sbp, out, scale=scale, progress=lambda pct: ft.unit(what=f'{pct}%'))
        task.unit(what='frames + audio')
        render_s = round(time.monotonic() - t0, 1)
        raw = work / 'draft-raw.mp4'; out.rename(raw)            # loudness to the platform target (-14 LUFS, peaks under -1.5 dBTP)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(raw), '-c:v', 'copy', '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-ar', '48000',
                        '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', str(out)], check=True)
        raw.unlink()
        webm = work / 'draft-preview.webm'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(out), '-vf', 'scale=540:-2', '-c:v', 'libvpx-vp9', '-b:v', '900k', '-deadline', 'realtime',
                        '-cpu-used', '8', '-row-mt', '1', '-c:a', 'libopus', '-b:a', '64k', str(webm)], check=True)
        task.unit(what='preview')
        poster = work / 'poster.jpg'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', '0.6', '-i', str(out), '-frames:v', '1', '-vf', 'scale=360:-2', str(poster)], check=True)
        dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(out)],
                                   capture_output=True, text=True).stdout.strip())
        rec = {'id': rid, 'state': 'ok', 'storyboard_v': sbrec['v'], 'file': studio.put_file(pid, out, 'mp4'),
               'poster': studio.put_file(pid, poster, 'jpg'), 'preview': studio.put_file(pid, webm, 'webm'), 'seconds': round(dur, 2), 'render_s': render_s,
               'size_mb': round(out.stat().st_size / 1e6, 2), 'label': 'DRAFT — draft voice, not for publishing',
               'check': chk[-40:], 'placeholders': [l for l in log.splitlines() if 'placeholder' in l.lower()][:5],
               'timeline': [{'id': s['id'], 'start': s['start'], 'end': round(s['start'] + s['dur'], 2)} for s in doc['scenes']],
               'engine_storyboard': studio.put(pid, json.dumps(esb, ensure_ascii=False).encode(), 'json'),
               'work': str(work.relative_to(studio.pdir(pid)))}
        task.unit(what='stored')
        studio.act(pid, 'render', rec, actor='system')
        return {'render': rid, 'seconds': rec['seconds']}
    except Exception as e:
        studio.act(pid, 'render', {'id': rid, 'state': 'failed', 'storyboard_v': sbrec['v'], 'error': f'{type(e).__name__}: {e}'[:600]},
                   actor='system')
        raise
