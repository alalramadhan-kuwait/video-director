"""AI video clips in a scene (storytelling rule 18l): people and places brought to life, never a watch.

The owner approved short generated clips (Seedance 2.5 on Higgsfield: 720p, 9:16, about 5 s, no audio) for some
scenes. The narration, the captions and the banner stay; the clip is only the picture. A film line says:

    clip: {file: films/private/halter/clips/l1a.mp4, label: مشهد بالذكاء الاصطناعي, fit: cover, mode: replace}

  mode: replace  (default) the clip fills the frame as the scene's picture: the template's picture and the world's
                 decor are dropped; the banner, captions, the label line and the HUD cards (words, cards) stay on top.
                 The shot plan may still zoom, within the clip's pixels (a 720p clip in a 1080p film barely zooms).
  mode: behind   the clip is the scene's backdrop: it replaces the world's decor (the set), and the scene's own
                 elements (a print, its velvet reveal, cards) stay over it, the camera free to come close to them.
  fit            cover (default) or contain
  end            pingpong (default) or hold: what a clip shorter than its scene does once it has played
  label          the line on screen that says it is generated, where a photo's credit goes («مشهد بالذكاء الاصطناعي»)

Timing (`timing`): a scene longer than its clip plays it slower, rate = clip / scene, never below MIN_RATE (0.7); if it
is still short, it runs backwards from its end at the same rate and on again (ping-pong), so the picture never stops.
A clip longer than its scene plays at 1.0 and is cut. The engine (vendor/studio-ext/clip.js) maps every frame from the
scene time alone (`clip_time` here is the same formula), so the render is frame-accurate on any worker.

A watch is never generated: a clip line whose template shows a watch photo must be `mode: behind`, so the real photo
stays on top (`problems`). Every clip is listed in credits.txt as CREDIT.
"""
from __future__ import annotations
import json, subprocess
from pathlib import Path

MIN_RATE = 0.7
LABEL = 'مشهد بالذكاء الاصطناعي'
CREDIT = 'فيديو بالذكاء الاصطناعي (Seedance 2.5 · Higgsfield)'
MODES = ('replace', 'behind')
ENDS = ('pingpong', 'hold')
OVERLAY = {'text', 'card', 'stamp', 'html', 'bubble', 'kit'}      # words and cards: kept over a clip that replaces the picture


def spec(ln: dict) -> dict | None:
    """The line's clip with its defaults, or None. Raises on a mode, fit or end it does not know."""
    c = ln.get('clip')
    if not c: return None
    c = {'file': c} if isinstance(c, str) else dict(c)
    if not c.get('file'): raise ValueError(f"{ln.get('id')}: clip needs its file:")
    c.setdefault('mode', 'replace'); c.setdefault('fit', 'cover'); c.setdefault('end', 'pingpong'); c.setdefault('label', '')   # the owner: «الناس تدري»; the credits and the platform's AI label say it, not the screen
    if c['mode'] not in MODES: raise ValueError(f"{ln.get('id')}: clip mode {c['mode']!r} is not one of {', '.join(MODES)}")
    if c['fit'] not in ('cover', 'contain'): raise ValueError(f"{ln.get('id')}: clip fit {c['fit']!r} is not cover or contain")
    if c['end'] not in ENDS: raise ValueError(f"{ln.get('id')}: clip end {c['end']!r} is not one of {', '.join(ENDS)}")
    return c


def watch_slot(ln: dict, photos: dict) -> str | None:
    """The watch photo a line's template shows (its asset), else None."""
    slot = (ln.get('params') or {}).get('asset')
    ph = photos.get(slot) if slot else None
    return slot if ph is not None and not ph.get('person') and not ph.get('not_a_watch') else None


def problems(film: dict) -> list[str]:
    """The clip rules a film breaks: a watch is never generated, so a clip over a watch photo plays behind it."""
    out, photos = [], film.get('photos') or {}
    for ln in film.get('lines', []):
        c = spec(ln)
        if not c: continue
        slot = watch_slot(ln, photos)
        if slot and c['mode'] != 'behind':
            out.append(f"{ln['id']}: a watch is never generated: the clip would replace the real photo {slot!r}; use mode: behind "
                       f"(the clip as the backdrop, the real photo on top)")
        if ln.get('photo') and c['mode'] == 'behind':
            out.append(f"{ln['id']}: a clip behind the scene and a photo behind its words (photo:) cannot both be the backdrop; keep one")
    return out


def probe(f: Path) -> dict:
    """{seconds, w, h, fps} of a clip (ffprobe)."""
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,r_frame_rate:format=duration',
                        '-of', 'json', str(f)], capture_output=True, text=True)
    j = json.loads(r.stdout or '{}')
    st = (j.get('streams') or [{}])[0]
    num, _, den = str(st.get('r_frame_rate', '24/1')).partition('/')
    fps = float(num) / float(den or 1) if float(den or 1) else 24.0
    return {'seconds': round(float((j.get('format') or {}).get('duration') or 0), 3), 'w': st.get('width'), 'h': st.get('height'), 'fps': round(fps, 3)}


def timing(clip: float, scene: float, least: float = MIN_RATE) -> dict:
    """How a clip of `clip` seconds fills a scene of `scene` seconds: {rate, plays, after}. `plays` is how long one pass
    lasts at that rate; `after` what fills the rest: 'cut' (the clip is long enough), else 'pingpong' (or a hold)."""
    if clip <= 0 or scene <= 0: return {'rate': 1.0, 'plays': clip, 'after': 'cut'}
    rate = 1.0 if clip >= scene else max(least, clip / scene)
    plays = clip / rate
    return {'rate': round(rate, 4), 'plays': round(plays, 3), 'after': 'cut' if plays >= scene - 1e-6 else 'pingpong'}


def clip_time(t: float, rate: float, length: float, end: str = 'pingpong', start: float = 0.0) -> float:
    """The clip's time at scene time t, exactly as the engine plays it (clip.js clipTime)."""
    c = start + max(0.0, t) * (rate or 1.0)
    if length <= 0 or c <= length: return max(0.0, c)
    if end == 'hold': return length
    p = c % (2 * length)
    return p if p <= length else 2 * length - p


def element(c: dict, src: str, dur: float, info: dict) -> dict:
    """The engine element for a clip (vendor/studio-ext/clip.js)."""
    tm = timing(float(info.get('seconds') or 0), dur)
    e = {'type': 'video', 'src': src, 'desc': c['label'], 'w': 720, 'h': 1280, 'x': 360, 'y': 640, 'fit': c['fit'], 'pos': c.get('pos', '50% 50%'),
         'rate': tm['rate'], 'end': c['end'], 'noBoil': True, 'noBlur': True, 'clip': True}
    if info.get('w') and info.get('h'): e['px'] = [info['w'], info['h']]
    if c['mode'] == 'behind':
        e.update(behind=True, depth=0)                 # pinned to the screen: the camera comes close to the print, not the clip
    return e


def _credit_line(e: dict) -> bool:
    return e.get('type') == 'text' and e.get('depth') == 0 and e.get('font') == 'cap' and e.get('y') == _credit_y()


def _credit_y() -> int:
    from .art import CREDIT_Y
    return CREDIT_Y


def label_line(text: str) -> dict:
    """The label on screen, where a photo's credit goes, styled as the AI-drawing credit («رسم بالذكاء الاصطناعي · …»)."""
    from .art import INK, PAPER
    return {'type': 'text', 'text': text, 'font': 'cap', 'size': 18, 'color': PAPER, 'paper': INK, 'x': 360, 'y': _credit_y(), 'depth': 0,
            'w': 600, 'align': 'center', 'z': 40, 'in': {'type': 'fade', 'at': .3}}


def apply(sc: dict, c: dict, src: str, dur: float, info: dict) -> dict:
    """Put the clip in a scene that is already drawn and dressed (art.scene_visual, sets.dress, moods.dress).
    replace: only the words and cards stay, over the clip (and the mood's light over it all); behind: the world's decor
    goes, the clip goes under the scene's own elements. The label goes on the credit line (joined to a photo's credit
    when the photo stays). The world's beds and sounds stay either way. Returns the scene."""
    clip = element(c, src, dur, info)
    els = sc.get('elements', [])
    if c['mode'] == 'replace':
        kept = [e for e in els if not e.get('world') and (e.get('type') in OVERLAY or e.get('mood')) and not _credit_line(e)]
        sc['elements'] = [clip] + kept
        if c['label']: sc['elements'].append(label_line(c['label']))
        sc['full_frame'] = True
    else:
        kept = [e for e in els if not e.get('world')]
        credit = next((e for e in kept if _credit_line(e)), None)
        if credit and c['label']: credit['text'] = f"{credit['text']} · {c['label']}"
        elif c['label']: kept.append(label_line(c['label']))
        sc['elements'] = [clip] + kept
    sc['clip'] = {'mode': c['mode'], 'rate': clip['rate'], 'end': c['end'], 'seconds': info.get('seconds')}
    return sc


def has_clip(sc: dict) -> bool:
    """Whether a scene plays a clip: it moves by itself (the stage law, the camera and the frozen checks count it)."""
    return any(e.get('type') == 'video' for e in sc.get('elements', []))
