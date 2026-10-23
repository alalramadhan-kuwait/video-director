"""A whole film from one film file (films/<name>.yaml), for the chat workflow: no per-film code.

The file holds the approved script line by line, each with its template from the motion catalogue and that template's
params, the photos (licensed, with their evidence) and the sources. `make()` then does every step with the brand config:
  voice      each line read by the draft voice (the brand's pronunciation applied), cached by its spoken text
  listen     Whisper hears every take; words it did not hear are reported (an omission is never silent)
  captions   the script's words timed to what Whisper heard, so captions follow the voice
  scenes     the catalogue template draws each line; only production-ready templates are accepted
  check      the engine's layout check and a still of every scene, which must be looked at before sending
  film       1080x1920, crf 24, the brand's music (ducked under the voice), the Time Keeper end card
  credits    sources, photo credits and the music credit, ready for the post caption
The voice here is the free DRAFT voice; the final narration is OmniVoice on the owner's computer (same file, --voice-dir).
"""
from __future__ import annotations
import hashlib, json, shutil, subprocess
from pathlib import Path

import yaml

from . import brand as B
from .copilot import commons
from .studio import art, checks, engine, sets, voice
from .studio.storyboard import VOICE_AT, TAIL, _endcard


def load(path) -> dict:
    f = yaml.safe_load(Path(path).read_text(encoding='utf-8'))
    for ln in f['lines']:
        if not art.production_ready(ln['template']):
            raise ValueError(f"{ln['id']}: template {ln['template']!r} is not production-ready (art/catalogue.yaml)")
    return f


def _seconds(p: Path) -> float:
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(p)],
                                capture_output=True, text=True).stdout)


def photos(film: dict, work: Path) -> dict:
    """Each photo slot as work/assets/<slot>.<ext>: the owner's own file, or a Commons file whose page states a free
    licence. A slot that cannot be filled is reported; the template then shows its «real photo needed» panel."""
    (work / 'assets').mkdir(parents=True, exist_ok=True)
    out = {}
    for slot, ph in (film.get('photos') or {}).items():
        have = next((f for f in (work / 'assets').glob(slot + '.*')), None)
        rec = work / 'assets' / f'{slot}.licence.json'
        if have and rec.is_file():
            out[slot] = json.loads(rec.read_text(encoding='utf-8')); continue
        if ph.get('file'):
            src = Path(ph['file']).expanduser()
            dst = work / 'assets' / (slot + src.suffix.lower()); shutil.copyfile(src, dst)
            meta = {'credit': ph.get('credit', ''), 'licence': ph.get('licence', 'owner'), 'page': ph.get('page', '')}
        else:
            c = commons.best(ph['query'], commons.candidates(ph['query']))
            if not c:
                out[slot] = {'missing': True, 'query': ph['query']}; continue
            ext = '.png' if c['url'].lower().split('?')[0].endswith('.png') else '.jpg'
            (work / 'assets' / (slot + ext)).write_bytes(commons.fetch(c['url']))
            meta = {'credit': commons.credit(c), 'licence': c['licence'], 'page': c['page'], 'title': c['title']}
        rec.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding='utf-8')
        out[slot] = meta
    return out


def take(line: dict, brand: str, vdir: Path) -> dict:
    """The line's voice take (cached by what is spoken), what Whisper heard, and the script words timed to it."""
    spoken = B.spoken(line.get('say') or line['text'], brand)
    speed = float((B.load(brand).get('narration') or {}).get('draft_speed', 1.0))   # the free draft voice reads slowly
    key = hashlib.sha256(f'{voice.PROVIDER}|{speed}|{spoken}'.encode()).hexdigest()[:10]
    wav, meta = vdir / f"{line['id']}-{key}.wav", vdir / f"{line['id']}-{key}.json"
    if not (wav.is_file() and meta.is_file()):
        vdir.mkdir(parents=True, exist_ok=True)
        mp3 = voice.synth(spoken)
        if speed != 1.0: mp3 = voice._ff('-i', '-', '-af', f'atempo={speed}', '-f', 'mp3', '-', inp=mp3)
        a = voice.trim(voice.decode(mp3))
        data = voice.encode(a, 'wav'); wav.write_bytes(data)
        heard = voice.hear(data)
        meta.write_text(json.dumps({'spoken': spoken, 'heard': heard, 'seconds': round(len(a) / voice.SR, 3)}, ensure_ascii=False),
                        encoding='utf-8')
    m = json.loads(meta.read_text(encoding='utf-8'))
    words = voice.align(checks.words(line['text']), m['heard'], m['seconds'])
    said = voice.align(checks.words(spoken), m['heard'], m['seconds'])
    # an omission is a word missing against both the script and what was meant to be said (Whisper writes years as digits,
    # the voice is given them as words; names are given as the brand says them)
    miss = [[w['w'] for w in ws if w['est'] and not w.get('heard')] for ws in (words, said)]
    return {'wav': wav, 'seconds': m['seconds'], 'spoken': spoken, 'heard': ' '.join(h['w'] for h in m['heard']), 'words': words,
            'not_heard': min(miss, key=len) if m['heard'] else []}


def loudness(src: Path, dst: Path):
    """The platform loudness target (-14 LUFS, peaks under -1.5 dBTP), the video stream untouched (as the studio does)."""
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(src), '-c:v', 'copy', '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-ar', '48000',
                    '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', str(dst)], check=True)


def make(path, out: Path, video=True, scale=1.5) -> dict:
    film = load(path)
    brand = film.get('brand', 'timekeeper')
    out = Path(out).resolve(); out.mkdir(parents=True, exist_ok=True)
    pics = photos(film, out)
    scenes, report = [], {'lines': [], 'photos': pics}
    for ln in film['lines']:
        t = take(ln, brand, out / 'voice')
        dur = round(VOICE_AT + t['seconds'] + TAIL + ln.get('pause', 0.25), 2)
        params = json.loads(json.dumps(ln.get('params', {}), ensure_ascii=False))
        for slot in art.NEEDS_ASSETS.get(ln['template'], lambda p: [])(params):           # a photo's credit goes on screen
            if pics.get(slot, {}).get('credit') and ln['template'] in ('product_reveal', 'product_macro'): params.setdefault('credit', pics[slot]['credit'])
        world = ln.get('set', film.get('set'))                               # the story world behind the template (sets.py)
        theme = ln.get('theme') or sets.theme_for(world, film.get('theme', 'tk-bone'))
        sc = sets.dress(art.scene_visual(ln['template'], params, theme, dur, banner=ln.get('banner')), world, dur, seed=ln['id'], template=ln['template'])
        same = scenes and scenes[-1].get('set') == world
        sc.update(id=ln['id'], dur=dur, voice=str(t['wav'].relative_to(out)), voiceAt=VOICE_AT,
                  words=[[round(VOICE_AT + w['s'], 2), w['w']] for w in t['words']],
                  transition=ln.get('transition', 'cut' if not scenes else ('slide' if same else 'fade')))     # a new world fades in
        scenes.append(sc)
        report['lines'].append({'id': ln['id'], 'seconds': dur, 'heard': t['heard'], 'not_heard': t['not_heard'], 'template': ln['template']})
    sb = {'width': 720, 'height': 1280, 'fps': 30, 'dir': 'rtl', **art.style(brand), 'scenes': scenes + _endcard(out)}
    (out / 'film.json').write_text(json.dumps(sb, ensure_ascii=False, indent=1), encoding='utf-8')
    report['layout'] = [l for l in engine.check(sb, out) if l.startswith('scene ')]
    starts = [sum(s['dur'] for s in scenes[:i]) for i in range(len(scenes))]
    shots = engine.stills(sb, out, [round(st + s['dur'] * .7, 2) for st, s in zip(starts, scenes)], scale=0.5)
    (out / 'scenes').mkdir(exist_ok=True)
    report['stills'] = []
    for s, f in zip(scenes, shots):
        dst = out / 'scenes' / f"{s['id']}.png"; shutil.copyfile(f, dst); report['stills'].append(str(dst))
    seconds = round(sum(s['dur'] for s in sb['scenes']), 1)
    mus = B.music(brand, seconds=seconds, seed=film.get('seed') or Path(path).stem, title=film.get('music'))
    report['music'] = mus and {k: mus[k] for k in ('title', 'licence', 'source', 'credit')}
    report['seconds'] = seconds
    if video:
        extra = ('--crf', B.load(brand).get('export', {}).get('crf', 24)) + (('--music', str(mus['file']), '--music-gain', mus['gain']) if mus else ())
        engine.video(out / 'film.json', out / 'film-raw.mp4', scale=scale, extra=extra)
        loudness(out / 'film-raw.mp4', out / 'film.mp4'); (out / 'film-raw.mp4').unlink()
        report['film'] = str(out / 'film.mp4'); report['size_mb'] = round((out / 'film.mp4').stat().st_size / 1e6, 1)
    credits = ['Sources:'] + [f"- {s}" for s in film.get('sources', [])]
    credits += ['Photos:'] + [f"- {v['credit']} ({v['page']})" for v in pics.values() if v.get('credit')]
    if mus: credits += ['Music:', mus['credit']]
    (out / 'credits.txt').write_text('\n'.join(credits) + '\n', encoding='utf-8')
    report['label'] = 'DRAFT VOICE (free) — the final narration is OmniVoice'
    (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')
    return report
