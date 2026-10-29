"""A whole film from one film file (films/<name>.yaml), for the chat workflow: no per-film code.

The file holds the approved script line by line, each with its template from the motion catalogue and that template's
params, the photos (licensed, with their evidence) and the sources. `make()` then does every step with the brand config:
  voice      each line read by the draft voice (the brand's pronunciation applied), cached by its spoken text
  listen     Whisper hears every take; words it did not hear are reported (an omission is never silent)
  captions   the script's words timed to what Whisper heard, so captions follow the voice
  scenes     the catalogue template draws each line; only production-ready templates are accepted
  check      the engine's layout check and a still of every scene, which must be looked at before sending
  film       1080x1920, crf 24, the brand's music (ducked under the voice, shifted so the cuts land on its beats),
             the Time Keeper end card
  platform   the film's `platform:` (else the brand's): its caption height, its length limit, words kept clear of the
             app's buttons (checked as drawn), a separate cover where the app asks for one, parts for a chat
  quality    measured, not judged by eye (director/quality.py): every word's contrast against what is behind it,
             no words crossing words, a finished first frame, no frozen stretch in the film
  hook       `hook: {text, em, dur}`: the hook written big over the first 1.5-3 s, the captions held back meanwhile
  credits    sources, photo credits and the music credit, ready for the post caption
  story      the storytelling rules, checked on every film (story_check):
             · a historical event (`event: true`) is shown with a historical photograph (archive_photo, archival_collage,
               newspaper_card) so the viewer sees it happened, or says why none exists (`no_photo:`)
             · a change (`change: true`: a new material, a new design) says why it happened (`because:`), in the narration
             · foreign names and English words are written in Latin letters (Panerai, Rolex), as the voice says them
             · the film opens where the story begins (its place and year: `city_zoom`), never a photo first and
               never an invented cartoon
             · a person on screen (`person:` on the photo) is introduced by name and never has words over the face
             · every scene has a related picture (a photo template, a photo behind the words: `photo:`, or a city
               zoom), and the picture is of the time the line speaks of (`year:` on each photo)
             · each scene shows only what is said in it (on-screen words share the narration's words or numbers)
             · every change of scene is led into: the line opens with a connective (و، ثم، لكن، بينما…) or a
               sentence that prepares the change (`closing: true` for an echo that ends the film)
             · the feeling of the story is named on the lines that carry it (`mood:` mystery, fear, sadness, tension, joy,
               wonder): it changes the light and the sound of the scene (director/studio/moods.py)
The voice is the free DRAFT voice unless `voice_dir` is given: a folder of takes read on the owner's computer, one per
line (OmniVoice: tools/voice_script.py, then omnivoice_narrate.py --lines-dir). Those takes are used as they are (no
speed change), Whisper still listens to each one, and the film is labelled with the voice and its licence.
"""
from __future__ import annotations
import hashlib, html, json, re, shutil, subprocess, time
from pathlib import Path

import yaml

from . import beats, platforms, quality, brand as B
from .copilot import commons
from .studio import art, checks, engine, moods, sets, voice
from .studio.storyboard import VOICE_AT, TAIL, _endcard


def load(path) -> dict:
    f = yaml.safe_load(Path(path).read_text(encoding='utf-8'))
    for ln in f['lines']:
        if not art.production_ready(ln['template']):
            raise ValueError(f"{ln['id']}: template {ln['template']!r} is not production-ready (art/catalogue.yaml)")
    return f


PHOTO_TEMPLATES = {'archive_photo', 'archival_collage', 'newspaper_card', 'product_reveal', 'product_macro', 'paper_cutout'}


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
    drawn_people = __import__('director.studio.drawn', fromlist=['DRESS']).DRESS
    for ln in lines:
        drawn = ln['template'] == 'paper_cutout' and not (ln.get('params') or {}).get('asset')      # a drawing, not evidence
        if ln.get('event') and (ln['template'] not in PHOTO_TEMPLATES or drawn) and not ln.get('photo') and not ln.get('no_photo'):
            out.append(f"{ln['id']}: a historical event with no historical photo (use archive_photo, or say why: no_photo)")
        kind = ((ln.get('params') or {}).get('drawn') or {}).get('kind')
        if kind and kind not in drawn_people:
            out.append(f"{ln['id']}: a watch is never drawn ({kind!r}): show its real photo (asset:); only a person may be drawn")
        if ln.get('change') and not ln.get('because'):
            out.append(f"{ln['id']}: a change without its reason (because:)")
        if ln.get('mood') and ln['mood'] not in moods.MOODS:
            out.append(f"{ln['id']}: unknown mood {ln['mood']!r} (one of {', '.join(moods.MOODS)})")
    if any(ln.get('event') for ln in lines) and not any(ln.get('mood') for ln in lines):
        out.append('the story has events but no line carries its feeling (mood:)')
    nar = (B.load(film.get('brand', 'timekeeper')).get('narration') or {})
    if nar.get('keep_latin'):                                            # foreign names in Latin letters (as Gérald Genta)
        arabic = {v: k for k, v in B.lexicon(film.get('brand', 'timekeeper')).items() if re.search(r'[A-Za-z]', k) and not re.search(r'[A-Za-z]', v)}
        for ln in lines:
            said = ' '.join([ln['text'], ln.get('say', '')] + on_screen(ln))
            for v, k in arabic.items():
                if re.search(r'(?<![\u0600-\u06FF])' + re.escape(v) + r'(?![\u0600-\u06FF])', said):
                    out.append(f"{ln['id']}: write «{v}» in English letters ({k}), in the script and on screen")
    photos = film.get('photos') or {}
    if lines and (lines[0]['template'] in PHOTO_TEMPLATES or lines[0].get('photo')) and not lines[0].get('opening_photo'):
        out.append(f"{lines[0]['id']}: open where the story begins (city_zoom of its place and year), not on a photo")
    for ln in lines:                                                     # a person on screen is introduced, and seen
        slot = ln.get('photo') or (ln.get('params') or {}).get('asset')
        who = (photos.get(slot) or {}).get('person') if slot else None
        if not who: continue
        if ln.get('photo'):
            out.append(f"{ln['id']}: {who} is behind the words (text on a face, no name): show the portrait with archive_photo and their name")
        elif not any(who in t for t in on_screen(ln)):
            out.append(f"{ln['id']}: {who} is on screen but not introduced (put the name in the banner or the card)")
    for ln in lines:                                                     # every scene has a related picture, of the right time
        slot = ln.get('photo') or (ln.get('params') or {}).get('asset')
        if ln is lines[0]: continue                                      # the opening is a drawing from the archive
        if not slot and ln['template'] != 'city_zoom' and not ln.get('no_photo') and not (ln.get('params') or {}).get('drawn'):
            out.append(f"{ln['id']}: no picture (give it a related photo: photo: <slot>, or say why: no_photo)")
        py = (photos.get(slot) or {}).get('year') if slot else None
        ys = [int(y) for y in re.findall(r'(?<!\d)(1[5-9]\d\d|20\d\d)(?!\d)', ln['text'])]
        modern = 'modern' in ((photos.get(slot) or {}).get('watch') or '') and any('حديث' in t for t in on_screen(ln))   # said so on screen
        if py and ys and min(abs(py - y) for y in ys) > 15 and not modern:
            out.append(f"{ln['id']}: the photo is from about {py} but the line speaks of {', '.join(map(str, ys))}")
        if slot and slot not in photos:
            out.append(f"{ln['id']}: photo slot {slot!r} is not in photos:")
    models = sorted(set((B.load(film.get('brand', 'timekeeper')).get('watch_models') or {}).get('names', []) + film.get('models', [])), key=len, reverse=True)
    for ln in lines:                                                     # a model that is named is the model that is shown (rule 12i)
        slot = ln.get('photo') or (ln.get('params') or {}).get('asset')
        ph = (photos.get(slot) or {}) if slot else {}
        if not slot or ph.get('person') or ph.get('not_a_watch'): continue
        named, rest = [], ' '.join([ln['text']] + on_screen(ln))
        for m in models:                                                 # the longest name first: «Royal Oak Offshore» is not «Royal Oak»
            if re.search(r'(?<![A-Za-z])' + re.escape(m) + r'(?![A-Za-z])', rest, re.I):
                named.append(m); rest = re.sub(re.escape(m), ' ', rest, flags=re.I)
        shows = ph.get('watch')
        if named and not shows:
            out.append(f"{ln['id']}: names {', '.join(named)}: say what photo {slot!r} shows (watch: brand, model, reference; or not_a_watch: true)")
            continue
        wrong = [m for m in named if m.lower() not in (shows or '').lower()]
        if wrong:
            out.append(f"{ln['id']}: names {', '.join(wrong)} but the photo shows {shows}: collectors see it at once (show that very model, or no watch)")
    for ln in lines:                                                     # each scene shows what is being said in it
        said = ln['text'] + ' ' + ln.get('say', '')
        for t in on_screen(ln):
            if not ln.get('screen_ok') and not _says(t, said):
                out.append(f"{ln['id']}: the screen shows «{t}», which this line does not say")
    for prev, ln in zip(lines, lines[1:]):                               # every change of scene is led into
        first = (checks.words(ln['text']) or [''])[0]
        if ln.get('closing') or first in LEADS or (first[:1] in 'وف' and len(first) > 2): continue
        out.append(f"{ln['id']}: begins without leading in from {prev['id']} (open with وبينما، لكن، ثم، وبعد… or a sentence that prepares the change)")
    hook = film.get('hook')
    if hook and lines:                                                   # the hook is the story's own words, not a teaser it never keeps
        st = lambda t: {checks.stem(w) for w in checks.words(t) if len(checks.stem(w)) >= 3 or w.isdigit()}
        said = st(' '.join(ln['text'] + ' ' + ln.get('say', '') for ln in lines[:2]))
        mine = st(hook['text'].replace('|', ' '))
        near = lambda x: any(x == y or (len(x) >= 4 and len(y) >= 4 and x[:4] == y[:4]) for y in said)
        if mine and sum(map(near, mine)) / len(mine) < 0.6:          # most of its words are the narration's own
            out.append(f"hook «{hook['text']}»: not said in the opening lines (take it from what the narration says)")
    last = None                                                          # told in order: a year never goes back unless it says so
    for ln in lines:
        ys = [int(y) for y in re.findall(r'(?<!\d)(1[5-9]\d\d|20\d\d)(?!\d)', ln['text'])]
        if not ys: continue
        if last and ys[0] < last[1] and not ln.get('flashback'):
            out.append(f"{ln['id']}: {ys[0]} comes after {last[1]} ({last[0]}): out of order (or mark it flashback: true)")
        last = (ln['id'], max(ys))
    return out


def hook_seconds(hook: dict) -> float:
    n = len(checks.words(hook['text'].replace('|', ' ')))
    return float(hook.get('dur') or min(3.0, max(1.6, 0.9 + 0.25 * n)))


def hook_card(sc: dict, hook: dict) -> float:
    """The hook written big over the opening (from video-ad-editor's hook card): a few words from the story, readable
    from the first frame, gone after `dur` seconds. The captions wait until it has gone: two texts at once and the viewer
    reads neither. `em` words are in the brand's gold; «|» breaks the line. Returns the hook's length in seconds."""
    dur = hook_seconds(hook)
    dark = art.ink_for(sc.get('theme')) == art.PAPER
    body = html.escape(hook['text'])
    for e in hook.get('em') or []:
        body = body.replace(html.escape(e), f'<span style="color:{art.GOLD}">{html.escape(e)}</span>')
    body = body.replace('|', '<br>')
    longest = max(len(l.strip()) for l in hook['text'].split('|'))
    size = hook.get('size') or max(36, min(58, int(600 / (0.5 * longest))))      # each line fits on one line
    ink = art.PAPER if dark else art.INK
    band = 'background:rgba(5,9,16,.78);' if dark else 'background:rgba(243,240,232,.86);'
    sc['elements'].append({'type': 'html', 'w': 660, 'h': 300, 'x': 360, 'y': hook.get('y', 400), 'z': 60, 'still': True,
                           'html': (f'<div style="width:660px;height:300px;display:flex;align-items:center;justify-content:center">'
                                    f'<div style="{band}border-radius:18px;padding:18px 26px;text-align:center;direction:rtl;'
                                    f'font-family:Cairo,sans-serif;font-weight:800;font-size:{size}px;line-height:1.35;color:{ink};white-space:nowrap">'
                                    f'{body}</div></div>'),
                           'in': {'type': 'rise', 'at': 0.05, 'dur': .4}, 'out': {'type': 'fade', 'at': round(dur - .3, 2), 'dur': .3}})
    sc['words'] = [w for w in sc.get('words', []) if w[0] >= dur]
    return dur


def _upright(f: Path):
    """A phone photo stores its turn in EXIF and the pixels sideways: turn the pixels so every tool sees it upright."""
    from PIL import Image, ImageOps
    with Image.open(f) as im:
        if (im.getexif() or {}).get(0x0112, 1) == 1: return
        up = ImageOps.exif_transpose(im)
    up.save(f, quality=95) if f.suffix.lower() in ('.jpg', '.jpeg') else up.save(f)


def _aspect(f: Path) -> float | None:
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=p=0', str(f)],
                       capture_output=True, text=True).stdout.strip().split(',')
    return round(int(r[0]) / int(r[1]), 3) if len(r) == 2 and r[1].isdigit() else None


def _seconds(p: Path) -> float:
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(p)],
                                capture_output=True, text=True).stdout)


def photos(film: dict, work: Path) -> dict:
    """Each photo slot as work/assets/<slot>.<ext>: the owner's own file, a Commons file whose page states a free
    licence, or a credited photo from another page (`url:` with `page:` and `credit:`; the owner's choice, rule 12j:
    downloaded at build time, never kept in the public repository). A slot that cannot be filled is reported; the
    template then shows its «real photo needed» panel."""
    (work / 'assets').mkdir(parents=True, exist_ok=True)
    out = {}
    for slot, ph in (film.get('photos') or {}).items():
        have = next((f for f in (work / 'assets').glob(slot + '.*')), None)
        rec = work / 'assets' / f'{slot}.licence.json'
        if have and rec.is_file():
            out[slot] = json.loads(rec.read_text(encoding='utf-8')); continue
        if ph.get('file'):
            src = Path(ph['file']).expanduser()
            if not src.is_absolute(): src = engine.ROOT / src                # films/assets/ (free) or films/private/ (never in git)
            if not src.is_file():
                out[slot] = {'missing': True, 'query': str(ph['file'])}; continue
            dst = work / 'assets' / (slot + src.suffix.lower()); shutil.copyfile(src, dst)
            meta = {'credit': ph.get('credit', ''), 'licence': ph.get('licence', 'owner'), 'page': ph.get('page', '')}
            if ph.get('licence') == 'credited': meta['credited'] = True
        elif ph.get('url'):                                                  # a credited photo from its page (rule 12j)
            if not (ph.get('page') and ph.get('credit')):
                raise ValueError(f"photo {slot}: a photo from the web needs its page: and its credit: (rule 12j)")
            try:
                data = commons.fetch(ph['url'])
            except OSError as e:
                out[slot] = {'missing': True, 'query': ph['url'], 'why': str(e)[:120]}; continue
            ext = '.png' if ph['url'].lower().split('?')[0].endswith('.png') else '.jpg'
            (work / 'assets' / (slot + ext)).write_bytes(data)
            meta = {'credit': ph['credit'], 'licence': ph.get('licence', 'credited (the owner\'s choice)'), 'page': ph['page'], 'credited': True}
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
        _upright(next((work / 'assets').glob(slot + '.[jp]*')))
        meta['aspect'] = _aspect(next((work / 'assets').glob(slot + '.[jp]*')))
        rec.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding='utf-8')
        out[slot] = meta
    for slot, ph in (film.get('photos') or {}).items():                   # a watch is named on screen as the model it is (rule 12i)
        if ph.get('watch') and not out[slot].get('missing'):
            out[slot] = {**out[slot], 'credit': ph['watch'] + ' · ' + out[slot].get('credit', '')}
    return out


def cutout(slot: str, work: Path, person: bool = False) -> dict:
    """The subject of a photo cut out of its background (tools/cutout_photo.py, rembg, free and local), cached as
    assets/<slot>_cut.png with its record. `whole` says whether the photo shows it whole (a portrait may stop at the
    shoulders). The tool runs with VD_CUTOUT_PYTHON (a Python with rembg installed), else this Python."""
    import os, sys
    rec = work / 'assets' / f'{slot}_cut.json'
    if rec.is_file():
        return json.loads(rec.read_text(encoding='utf-8'))
    src = next((f for f in (work / 'assets').glob(slot + '.*') if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp')), None)
    if src is None:
        return {'whole': False, 'why': 'no photo'}
    py = os.environ.get('VD_CUTOUT_PYTHON', sys.executable)
    r = subprocess.run([py, str(engine.ROOT / 'tools/cutout_photo.py'), str(src), str(work / 'assets' / f'{slot}_cut.png')] + (['--person'] if person else []),
                       capture_output=True, text=True)
    line = (r.stdout.strip().splitlines() or ['{}'])[-1]
    try:
        out = json.loads(line)
    except ValueError:
        return {'whole': False, 'why': (r.stderr or r.stdout)[-300:]}
    if person and out.get('cut_sides') == ['bottom']:
        out['whole'] = True                                   # a portrait: the person as photographed, cut at the waist
    rec.write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
    return out


def voice_script(film: dict) -> list[dict]:
    """What the voice reads, line by line: {id, text} with `say` (years as words) where the line has one."""
    return [{'id': ln['id'], 'text': (ln.get('say') or ln['text']).strip()} for ln in film['lines']]


def given_take(line: dict, src: Path, vdir: Path) -> tuple[Path, Path]:
    """A take read elsewhere (src/<id>.wav), copied into the film folder at 24 kHz mono with what Whisper heard in it;
    cached by the take's own bytes, so a line read again is listened to again."""
    data = src.read_bytes()
    key = hashlib.sha256(data).hexdigest()[:10]
    wav, meta = vdir / f"{line['id']}-given-{key}.wav", vdir / f"{line['id']}-given-{key}.json"
    if not (wav.is_file() and meta.is_file()):
        vdir.mkdir(parents=True, exist_ok=True)
        a = voice.trim(voice.decode(data))
        out = voice.encode(a, 'wav'); wav.write_bytes(out)
        meta.write_text(json.dumps({'heard': voice.hear(out), 'seconds': round(len(a) / voice.SR, 3), 'source': str(src)},
                                   ensure_ascii=False), encoding='utf-8')
    return wav, meta


def take(line: dict, brand: str, vdir: Path, given: Path | None = None) -> dict:
    """The line's voice take (cached by what is spoken), what Whisper heard, and the script words timed to it.
    `given` is a folder of takes read elsewhere (one <id>.wav per line), used instead of the draft voice."""
    spoken = B.spoken(line.get('say') or line['text'], brand)
    speed = float((B.load(brand).get('narration') or {}).get('draft_speed', 1.0))   # the free draft voice reads slowly
    key = hashlib.sha256(f'{voice.PROVIDER}|{speed}|{spoken}'.encode()).hexdigest()[:10]
    wav, meta = vdir / f"{line['id']}-{key}.wav", vdir / f"{line['id']}-{key}.json"
    if given is not None:
        wav, meta = given_take(line, given / f"{line['id']}.wav", vdir)
    elif not (wav.is_file() and meta.is_file()):
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
    """The platform loudness target (-14 LUFS, peaks under -1.5 dBTP), the video stream untouched (as the studio does).
    Two passes: the film is measured first and normalised with those figures (one pass fell 2.4 LU short on a
    quieter, more dynamic voice)."""
    target = 'I=-14:TP=-2:LRA=11'                                  # -2 dBTP so the AAC encode stays under -1.5
    pre = 'alimiter=limit=0.35:attack=2:release=60:level=false,'      # tame the voice's lone peaks so the gain can be linear
    r = subprocess.run(['ffmpeg', '-hide_banner', '-i', str(src), '-af', f'{pre}loudnorm={target}:print_format=json', '-f', 'null', '-'],
                       capture_output=True, text=True)
    m = re.search(r'\{[^{}]*"input_i"[^{}]*\}', r.stderr)
    af = f'{pre}loudnorm={target}'
    if m:
        j = json.loads(m.group(0))
        af += (f":measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}"
               f":measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(src), '-c:v', 'copy', '-af', af, '-ar', '48000',
                    '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', str(dst)], check=True)


def voice_label(voice_dir: Path | None) -> tuple[str, str]:
    """(label, licence) of the narration: the free draft voice, or the takes in voice_dir as their records describe them."""
    if voice_dir is None:
        return 'DRAFT VOICE (free) — the final narration is OmniVoice', ''
    recs = [json.loads(f.read_text(encoding='utf-8')) for f in sorted(Path(voice_dir).glob('*.json'))]
    lic = {r.get('license_note', '') for r in recs if r.get('license_note')}
    prov = {r.get('provider', '') for r in recs if r.get('provider')}
    if 'omnivoice' in prov:                                  # the owner's chosen narration voice
        return 'OmniVoice narration', ''
    if prov == {'voxcpm2'}:
        return 'VoxCPM2 narration (Apache-2.0 model, commercial use permitted)', '; '.join(sorted(lic))
    return 'Narration from ' + str(voice_dir), '; '.join(sorted(lic))


def split(film: Path, cuts: list[tuple[float, float]], mb: float) -> list[Path]:
    """The film in parts (film-part1.mp4 …), each re-encoded at the bitrate that keeps it under `mb` megabytes."""
    out = []
    for i, (a, b) in enumerate(cuts, 1):
        dst = film.with_name(f'{film.stem}-part{i}.mp4')
        kbps = int(mb * 8e6 * 0.92 / (b - a) / 1000) - 160                  # 8 % margin for the container; 160k audio
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{a:.3f}', '-to', f'{b:.3f}', '-i', str(film), '-c:v', 'libx264',
                        '-b:v', f'{kbps}k', '-maxrate', f'{kbps}k', '-bufsize', f'{2 * kbps}k', '-preset', 'slow', '-pix_fmt', 'yuv420p',
                        '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', str(dst)], check=True)
        out.append(dst)
    return out


def make(path, out: Path, video=True, scale=1.5, voice_dir: Path | None = None) -> dict:
    film = load(path)
    brand = film.get('brand', 'timekeeper')
    out = Path(out).resolve(); out.mkdir(parents=True, exist_ok=True)
    if voice_dir is not None:
        voice_dir = Path(voice_dir).expanduser().resolve()
        missing = [ln['id'] for ln in film['lines'] if not (voice_dir / f"{ln['id']}.wav").is_file()]
        if missing:
            raise FileNotFoundError(f'no take in {voice_dir} for: ' + ', '.join(missing))
    pics = photos(film, out)
    plat_id, plat = platforms.of(film, B.load(brand))
    scenes, report = [], {'lines': [], 'photos': pics, 'story': story_check(film), 'platform': plat['name']}
    for ln in film['lines']:
        t = take(ln, brand, out / 'voice', given=voice_dir)
        gap = film.get('gap') or {}                                          # a slower voice keeps its words, the silences shorten
        dur = round(VOICE_AT + t['seconds'] + gap.get('tail', TAIL) + ln.get('pause', gap.get('pause', 0.25)), 2)
        params = json.loads(json.dumps(ln.get('params', {}), ensure_ascii=False))
        for slot in art.NEEDS_ASSETS.get(ln['template'], lambda p: [])(params):           # a photo's credit goes on screen
            if pics.get(slot, {}).get('credit') and ln['template'] in ('product_reveal', 'product_macro', 'archive_photo', 'blueprint'): params.setdefault('credit', pics[slot]['credit'])
            if ln['template'] in ('archive_photo', 'blueprint') and pics.get(slot, {}).get('aspect'): params.setdefault('aspect', pics[slot]['aspect'])
        template = ln['template']
        if template == 'paper_cutout' and params.get('asset'):                # the whole subject, cut out (rule 12h)
            slot = params['asset']
            person = bool((film.get('photos') or {}).get(slot, {}).get('person'))
            c = cutout(slot, out, person) if not pics.get(slot, {}).get('missing') else {'whole': False, 'why': 'no photo'}
            why = c.get('cut_sides') or c.get('why')
            if c.get('whole'):
                params.update(aspect=c['aspect'], person=person)
                if pics.get(slot, {}).get('credit'): params.setdefault('credit', pics[slot]['credit'] + ' · cut out')
            elif person and params.get('drawn'):                             # no photo shows the person whole: drawn in our style
                params.pop('asset'); report.setdefault('drawn', []).append(f"{ln['id']}: {slot} is not whole in its photo ({why}): drawn")
            elif person:
                report.setdefault('drawn', []).append(f"{ln['id']}: {slot} is not whole in its photo ({why}): give it a drawn: fallback")
                params.update(aspect=c.get('aspect', .75), person=person)
            else:                                                            # a watch is never drawn: its real photo, uncut
                template = 'archive_photo'
                params = {k: v for k, v in params.items() if k in ('asset', 'desc', 'card')}
                if pics.get(slot, {}).get('credit'): params['credit'] = pics[slot]['credit']
                if pics.get(slot, {}).get('aspect'): params['aspect'] = pics[slot]['aspect']
                report.setdefault('drawn', []).append(f"{ln['id']}: {slot} is not whole in its photo ({why}): shown as its photo, uncut")
        if params.get('land_on'):                                            # a number lands when the voice says it (rule 18b)
            hit = next((w for w in t['words'] if w['w'] == str(params['land_on'])), None)
            params.pop('land_on')
            if hit: params['land'] = round(VOICE_AT + hit['s'], 2)
        world = ln.get('set', film.get('set'))                               # the story world behind the template (sets.py)
        theme = ln.get('theme') or ('tk-ink' if ln.get('photo') else sets.theme_for(world, film.get('theme', 'tk-bone')))
        sc = art.scene_visual(template, params, theme, dur, banner=ln.get('banner'))
        if ln.get('photo'):                                                  # a scene of words gets its related photo behind
            art.backdrop(sc, ln['photo'], dur, credit=pics.get(ln['photo'], {}).get('credit', ''))
        sc = sets.dress(sc, world, dur, seed=ln['id'], template=template)
        moods.dress(sc, ln.get('mood'), dur)                                 # the feeling of the line: light and sound
        same = scenes and scenes[-1].get('set') == world
        sc.update(id=ln['id'], dur=dur, voice=str(t['wav'].relative_to(out)), voiceAt=VOICE_AT,
                  words=[[round(VOICE_AT + w['s'], 2), w['w']] for w in t['words']],
                  transition=ln.get('transition', 'cut' if not scenes else ('slide' if same else 'fade')))     # a new world fades in
        scenes.append(sc)
        report['lines'].append({'id': ln['id'], 'seconds': dur, 'heard': t['heard'], 'not_heard': t['not_heard'], 'template': template})
    hook_end = hook_card(scenes[0], film['hook']) if film.get('hook') and scenes else None
    ending = _endcard(out)
    sb = {'width': 720, 'height': 1280, 'fps': 30, 'dir': 'rtl', 'captionY': plat['caption_y'], **art.style(brand),
          'scenes': scenes + ending}
    seconds = round(sum(s['dur'] for s in sb['scenes']), 1)
    mus = B.music(brand, seconds=seconds, seed=film.get('seed') or Path(path).stem, title=film.get('music'))
    report['music'] = mus and {k: mus[k] for k in ('title', 'licence', 'source', 'credit')}
    if mus:                                                              # the cuts land on the music's beats
        cuts = [round(sum(s['dur'] for s in sb['scenes'][:i]), 3) for i in range(1, len(sb['scenes']))]
        al = beats.align(Path(mus['file']), cuts, seconds, out / 'music-aligned.flac')
        mus['file'] = al['file']
        punched = 0
        if film.get('beats') == 'punch':                                 # a small push on the scenes that start on a beat
            punched = sum(beats.punch(sc) for sc, ok in zip(sb['scenes'][1:], al['on_beat']) if ok)
        report['beats'] = {'offset': al['offset'], 'on_beat': al['hits'], 'cuts': al['cuts'], 'punched': punched}
    (out / 'film.json').write_text(json.dumps(sb, ensure_ascii=False, indent=1), encoding='utf-8')
    report['layout'] = [l for l in engine.check(sb, out) if l.startswith('scene ')]
    safe = engine.safe(sb, out, platforms.zones(plat)) if plat['zones'] else []
    report['safe'] = [l for l in safe if l.startswith('safe HARD')]
    report['safe_caution'] = sum(1 for l in safe if l.startswith('safe caution'))
    report['length'] = platforms.length_warning(plat, seconds)
    report['quality'] = quality.check(sb, out, seconds)                  # contrast, words over words, a finished first frame
    starts = [sum(s['dur'] for s in scenes[:i]) for i in range(len(scenes))]
    shots = engine.stills(sb, out, [round(st + s['dur'] * .7, 2) for st, s in zip(starts, scenes)], scale=0.5)
    (out / 'scenes').mkdir(exist_ok=True)
    report['stills'] = []
    for s, f in zip(scenes, shots):
        dst = out / 'scenes' / f"{s['id']}.png"; shutil.copyfile(f, dst); report['stills'].append(str(dst))
    report['seconds'] = seconds
    if plat['cover']:                                                    # the app asks for a cover: the hook, or the opening
        t = (hook_end - .15) if hook_end else scenes[0]['dur'] * .7
        f = engine.stills(sb, out, [round(t, 2)], scale=1.5)[0]           # in out/: the storyboard's paths are relative to it
        shutil.copyfile(f, out / 'cover.png'); report['cover'] = str(out / 'cover.png')
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
        report['quality'] += quality.runs(quality.frozen(out / 'film.mp4', ending=sum(s['dur'] for s in ending)))   # no still stretch in the finished film
        if plat['parts']:                                                # a chat: parts cut between scenes, each under its limit
            starts = [sum(s['dur'] for s in sb['scenes'][:i]) for i in range(len(sb['scenes']))]
            report['parts'] = [str(p) for p in split(out / 'film.mp4', platforms.parts(starts, [s['dur'] for s in sb['scenes']],
                                                                                        plat['part_seconds']), plat['part_mb'])]
    credits = ['Sources:'] + [f"- {s}" for s in film.get('sources', [])]
    credits += ['Photos:'] + [f"- {v['credit']} ({v['page']})" for v in pics.values() if v.get('credit')]
    if mus: credits += ['Music:', mus['credit']]
    label, lic = voice_label(voice_dir)
    credits += ['Narration:', label + (f' ({lic})' if lic else '')]
    (out / 'credits.txt').write_text('\n'.join(credits) + '\n', encoding='utf-8')
    report['label'] = label
    (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')
    return report
