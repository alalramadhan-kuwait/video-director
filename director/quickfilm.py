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
  story      the storytelling rules, checked on every film (story_check):
             · a historical event (`event: true`) is shown with a historical photograph (archive_photo, archival_collage,
               newspaper_card) so the viewer sees it happened, or says why none exists (`no_photo:`)
             · a change (`change: true`: a new material, a new design) says why it happened (`because:`), in the narration
             · every scene has a related picture (a photo template, a photo behind the words: `photo:`, or a city
               zoom), and the picture is of the time the line speaks of (`year:` on each photo)
             · each scene shows only what is said in it (on-screen words share the narration's words or numbers)
             · every change of scene is led into: the line opens with a connective (و، ثم، لكن، بينما…) or a
               sentence that prepares the change (`closing: true` for an echo that ends the film)
             · the feeling of the story is named on the lines that carry it (`mood:` mystery, fear, sadness, tension, joy,
               wonder): it changes the light and the sound of the scene (director/studio/moods.py)
The voice here is the free DRAFT voice; the final narration is OmniVoice on the owner's computer (same file, --voice-dir).
"""
from __future__ import annotations
import hashlib, json, re, shutil, subprocess, time
from pathlib import Path

import yaml

from . import brand as B
from .copilot import commons
from .studio import art, checks, engine, moods, sets, voice
from .studio.storyboard import VOICE_AT, TAIL, _endcard


def load(path) -> dict:
    f = yaml.safe_load(Path(path).read_text(encoding='utf-8'))
    for ln in f['lines']:
        if not art.production_ready(ln['template']):
            raise ValueError(f"{ln['id']}: template {ln['template']!r} is not production-ready (art/catalogue.yaml)")
    return f


PHOTO_TEMPLATES = {'archive_photo', 'archival_collage', 'newspaper_card', 'product_reveal', 'product_macro'}


SCREEN = ('text', 'title', 'body', 'label', 'value', 'values', 'name', 'sub', 'card', 'quote', 'who', 'header', 'banner', 'lines',
          'rows', 'events', 'stamp', 'labels', 'pins', 'year', 'columns')
LEADS = {'ثم', 'لكن', 'لكنّ', 'غير', 'بينما', 'حين', 'عندما', 'بعد', 'إلى', 'الى', 'حتى', 'هناك', 'أما', 'في', 'منذ', 'لذلك', 'لأن', 'مع', 'هكذا'}


def on_screen(ln: dict) -> list[str]:
    """Every piece of text the scene shows (not the captions, which are the narration itself; not credits or sources)."""
    out = []
    def walk(v, key=None):
        if isinstance(v, dict):
            for k, x in v.items():
                if k in SCREEN: walk(x, k)
        elif isinstance(v, list):
            for x in v: walk(x, key)
        elif isinstance(v, str) and key in SCREEN and v.strip():
            out.append(v.strip())
    walk({'banner': ln.get('banner')}); walk(ln.get('params', {}), 'lines')
    return out


def _says(screen: str, narration: str) -> bool:
    """Whether a piece of on-screen text belongs to what is being said: a shared word (by its stem) or number."""
    st = lambda t: {checks.stem(w) for w in checks.words(t) if len(checks.stem(w)) >= 3 or w.isdigit()}
    a, b = st(screen), st(narration)
    return any(x == y or (len(x) >= 4 and len(y) >= 4 and x[:4] == y[:4]) for x in a for y in b)


def story_check(film: dict) -> list[str]:
    """The storytelling rules this film breaks, in plain words (an empty list is a pass)."""
    out, lines = [], film['lines']
    for ln in lines:
        if ln.get('event') and ln['template'] not in PHOTO_TEMPLATES and not ln.get('photo') and not ln.get('no_photo'):
            out.append(f"{ln['id']}: a historical event with no historical photo (use archive_photo, or say why: no_photo)")
        if ln.get('change') and not ln.get('because'):
            out.append(f"{ln['id']}: a change without its reason (because:)")
        if ln.get('mood') and ln['mood'] not in moods.MOODS:
            out.append(f"{ln['id']}: unknown mood {ln['mood']!r} (one of {', '.join(moods.MOODS)})")
    if any(ln.get('event') for ln in lines) and not any(ln.get('mood') for ln in lines):
        out.append('the story has events but no line carries its feeling (mood:)')
    photos = film.get('photos') or {}
    for ln in lines:                                                     # every scene has a related picture, of the right time
        slot = ln.get('photo') or (ln.get('params') or {}).get('asset')
        if not slot and ln['template'] != 'city_zoom' and not ln.get('no_photo'):
            out.append(f"{ln['id']}: no picture (give it a related photo: photo: <slot>, or say why: no_photo)")
        py = (photos.get(slot) or {}).get('year') if slot else None
        ys = [int(y) for y in re.findall(r'(?<!\d)(1[5-9]\d\d|20\d\d)(?!\d)', ln['text'])]
        if py and ys and min(abs(py - y) for y in ys) > 15:
            out.append(f"{ln['id']}: the photo is from about {py} but the line speaks of {', '.join(map(str, ys))}")
        if slot and slot not in photos:
            out.append(f"{ln['id']}: photo slot {slot!r} is not in photos:")
    for ln in lines:                                                     # each scene shows what is being said in it
        said = ln['text'] + ' ' + ln.get('say', '')
        for t in on_screen(ln):
            if not ln.get('screen_ok') and not _says(t, said):
                out.append(f"{ln['id']}: the screen shows «{t}», which this line does not say")
    for prev, ln in zip(lines, lines[1:]):                               # every change of scene is led into
        first = (checks.words(ln['text']) or [''])[0]
        if ln.get('closing') or first in LEADS or (first[:1] in 'وف' and len(first) > 2): continue
        out.append(f"{ln['id']}: begins without leading in from {prev['id']} (open with وبينما، لكن، ثم، وبعد… or a sentence that prepares the change)")
    last = None                                                          # told in order: a year never goes back unless it says so
    for ln in lines:
        ys = [int(y) for y in re.findall(r'(?<!\d)(1[5-9]\d\d|20\d\d)(?!\d)', ln['text'])]
        if not ys: continue
        if last and ys[0] < last[1] and not ln.get('flashback'):
            out.append(f"{ln['id']}: {ys[0]} comes after {last[1]} ({last[0]}): out of order (or mark it flashback: true)")
        last = (ln['id'], max(ys))
    return out


def _aspect(f: Path) -> float | None:
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=p=0', str(f)],
                       capture_output=True, text=True).stdout.strip().split(',')
    return round(int(r[0]) / int(r[1]), 3) if len(r) == 2 and r[1].isdigit() else None


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
            try:
                time.sleep(2)                                                # Commons asks tools to go slowly
                c = commons.best(ph['query'], commons.candidates(ph['query']))
                data = c and commons.fetch(c['url'])
            except OSError as e:                                             # busy or offline: this photo waits, the film goes on
                out[slot] = {'missing': True, 'query': ph['query'], 'why': str(e)[:120]}; continue
            if not c or not data:
                out[slot] = {'missing': True, 'query': ph['query']}; continue
            ext = '.png' if c['url'].lower().split('?')[0].endswith('.png') else '.jpg'
            (work / 'assets' / (slot + ext)).write_bytes(data)
            meta = {'credit': commons.credit(c), 'licence': c['licence'], 'page': c['page'], 'title': c['title']}
        meta['aspect'] = _aspect(next((work / 'assets').glob(slot + '.[jp]*')))
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
    scenes, report = [], {'lines': [], 'photos': pics, 'story': story_check(film)}
    for ln in film['lines']:
        t = take(ln, brand, out / 'voice')
        dur = round(VOICE_AT + t['seconds'] + TAIL + ln.get('pause', 0.25), 2)
        params = json.loads(json.dumps(ln.get('params', {}), ensure_ascii=False))
        for slot in art.NEEDS_ASSETS.get(ln['template'], lambda p: [])(params):           # a photo's credit goes on screen
            if pics.get(slot, {}).get('credit') and ln['template'] in ('product_reveal', 'product_macro', 'archive_photo'): params.setdefault('credit', pics[slot]['credit'])
            if ln['template'] == 'archive_photo' and pics.get(slot, {}).get('aspect'): params.setdefault('aspect', pics[slot]['aspect'])
        world = ln.get('set', film.get('set'))                               # the story world behind the template (sets.py)
        theme = ln.get('theme') or ('tk-ink' if ln.get('photo') else sets.theme_for(world, film.get('theme', 'tk-bone')))
        sc = art.scene_visual(ln['template'], params, theme, dur, banner=ln.get('banner'))
        if ln.get('photo'):                                                  # a scene of words gets its related photo behind
            art.backdrop(sc, ln['photo'], dur, credit=pics.get(ln['photo'], {}).get('credit', ''))
        sc = sets.dress(sc, world, dur, seed=ln['id'], template=ln['template'])
        moods.dress(sc, ln.get('mood'), dur)                                 # the feeling of the line: light and sound
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
        cap = B.load(brand).get('export', {}).get('max_mb')
        if cap and (out / 'film.mp4').stat().st_size / 1e6 > cap:          # too big to share: the same film, compressed harder
            crf = int(B.load(brand).get('export', {}).get('crf', 24))
            for step in (3, 5, 7):
                subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(out / 'film.mp4'), '-c:v', 'libx264', '-crf', str(crf + step), '-preset', 'slow',
                                '-pix_fmt', 'yuv420p', '-c:a', 'copy', '-movflags', '+faststart', str(out / 'film-small.mp4')], check=True)
                if (out / 'film-small.mp4').stat().st_size / 1e6 <= cap: break
            (out / 'film-small.mp4').replace(out / 'film.mp4'); report['crf'] = crf + step
        report['film'] = str(out / 'film.mp4'); report['size_mb'] = round((out / 'film.mp4').stat().st_size / 1e6, 1)
    credits = ['Sources:'] + [f"- {s}" for s in film.get('sources', [])]
    credits += ['Photos:'] + [f"- {v['credit']} ({v['page']})" for v in pics.values() if v.get('credit')]
    if mus: credits += ['Music:', mus['credit']]
    (out / 'credits.txt').write_text('\n'.join(credits) + '\n', encoding='utf-8')
    report['label'] = 'DRAFT VOICE (free) — the final narration is OmniVoice'
    (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')
    return report
