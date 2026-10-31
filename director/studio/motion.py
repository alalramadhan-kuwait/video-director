"""The camera of every scene: a real move, measured.

Étienne's review of Halter measured a film whose camera hardly moved: paper_cutout pushed 1.00 -> 1.02 over 10-12 s,
and the photo scenes stood at 1.00. The rule since then (storytelling rule 18d):
  * every scene's camera moves at least MIN (3 %): a push-in, a pull-back, a drift or a lateral dolly, chosen by the
    scene's seed so neighbouring scenes do not all move the same way;
  * a scene longer than LONG (5 s) gets a second picture event: a punch-in on a caption word (quickfilm, which knows
    when each word is said), or at least a change of speed half-way, so the picture never settles into a hold.
`amount()` is the measure the review and quality steps use (LONG_HOLD): the larger of how far the zoom travels and how
far the picture pans (screen pixels, against the 720-wide frame) over the scene, sampled as the engine plays the keys.

Shot sizes (`direct`, storytelling rule 18h; the idea of Bang Motion, MIT, © 2026 Bang Tutorial). A few % of zoom
reads as a still, so a directed scene changes SHOT SIZE on the words that carry it: wide (1.08-1.14), medium
(1.28-1.42), close-up (1.6-1.9), framed on the subject the words are about (a photo, a person's face, a number, a line
of words), never below FLOOR (1.08), eased, seeded by the line, then a slow push while the shot holds. A line steers it
with `shots: [{on: فبراير, to: close, focus: [x, y]}]` (focus in frame px of the 720x1280 frame; `at:` seconds instead
of `on:`; `nth:` for a repeated word; `to:` a size or a zoom number). A photo is never shown bigger than its own pixels
allow: the zoom is capped from the photo's real size (`cap`, the same limit as the engine's layout `soft` check). The
frame never shows the world's edge (the engine clamps a directed camera, as Bang Motion's frameOn does).
Cuts (`cut_focus`, `match`) and the stage law (`stage_law`: enough moving things, the zoom floor, no plain fade inside
one place) live here too, so quickfilm, the studio and the checks share them.
"""
from __future__ import annotations
import hashlib, math, random
from pathlib import Path

MIN, MAX = 0.03, 0.05                  # the move a scene gets when its own camera does less
LONG = 5.0                             # seconds: a scene longer than this gets a second picture event
W = 720
TOL = 1e-6

# the engine's easings (vendor/paper-story/engine/paper.js E); an unknown name falls back to inOutCubic, as there
EASE = {
    'linear': lambda t: t,
    'outCubic': lambda t: 1 - (1 - t) ** 3,
    'inCubic': lambda t: t ** 3,
    'inOutCubic': lambda t: 4 * t ** 3 if t < .5 else 1 - (-2 * t + 2) ** 3 / 2,
    'outBack': lambda t: 1 + 2.70158 * (t - 1) ** 3 + 1.70158 * (t - 1) ** 2,
    'inQuad': lambda t: t * t,
    'outQuart': lambda t: 1 - (1 - t) ** 4,
    'outExpo': lambda t: 1.0 if t >= 1 else 1 - 2 ** (-10 * t),
    'step': lambda t: 1.0 if t >= 1 else 0.0,
}


def val(spec, t: float, default: float) -> float:
    """A number or keyframes [[t, v, ease?], ...] at time t, exactly as the engine reads them."""
    if spec is None: return default
    if isinstance(spec, (int, float)): return float(spec)
    if isinstance(spec, list) and spec and isinstance(spec[0], list):
        if t <= spec[0][0]: return float(spec[0][1])
        for a, b in zip(spec, spec[1:]):
            if t <= b[0]:
                p = (t - a[0]) / ((b[0] - a[0]) or 1e-9)
                e = EASE.get(b[2] if len(b) > 2 else None, EASE['inOutCubic'])
                return a[1] + (b[1] - a[1]) * e(min(1.0, max(0.0, p)))
        return float(spec[-1][1])
    return default


def amount(sc: dict, dur: float | None = None) -> float:
    """How far the scene's camera moves: max(zoom change, pan on screen / 720), 0 for no camera."""
    cam = sc.get('camera') or {}
    dur = float(dur if dur is not None else sc.get('dur') or 4.0)
    if not cam: return 0.0
    n = max(2, int(dur / .05))
    zs, xs, ys = [], [], []
    for i in range(n + 1):
        t = dur * i / n
        z = val(cam.get('zoom'), t, 1.0)
        # where the frame's centre point of the stage lands on screen: 360 + (360 - cam.x) * zoom
        zs.append(z); xs.append((360 - val(cam.get('x'), t, 360)) * z); ys.append((640 - val(cam.get('y'), t, 640)) * z)
    # how far it travels (a pull-back that then punches in moves more than either alone, not less)
    zoom = math.exp(sum(abs(math.log(b / a)) for a, b in zip(zs, zs[1:]) if a > 0 and b > 0)) - 1
    pan = sum(math.hypot(x1 - x0, y1 - y0) for x0, x1, y0, y1 in zip(xs, xs[1:], ys, ys[1:])) / W
    return round(max(zoom, pan), 4)


def _rng(seed) -> random.Random:
    return random.Random(int(hashlib.sha256(str(seed).encode()).hexdigest()[:12], 16))


MOVES = ('push', 'pull', 'dolly_left', 'dolly_right', 'drift_up')


def move(dur: float, seed, kind: str | None = None, size: float | None = None) -> dict:
    """A camera move of 3-5 %, never zoomed out of the frame (zoom >= 1, and a dolly is zoomed in enough that a
    full-frame picture never shows its edge). Two keyframe segments with different speeds: no move is one flat ramp."""
    r = _rng(seed)
    kind = kind or r.choice(MOVES)
    a = round(size if size is not None else r.uniform(MIN + .005, MAX), 4)
    mid = round(dur * r.uniform(.4, .6), 2)
    k = r.choice((r.uniform(.2, .32), r.uniform(.6, .75)))   # how much of the move is done by `mid`: the speed changes there
    if kind in ('push', 'pull'):
        z0, z1 = (1.0, 1 + a) if kind == 'push' else (1 + a, 1.0)
        zm = round(z0 + (z1 - z0) * k, 4)
        c = r.uniform(150, 350)                              # it rises a little as it closes in: y follows the zoom, so the
        y = lambda z: round(640 - c * (z - 1), 1)            # frame's top edge never comes into view (y * zoom >= 640)
        return {'zoom': [[0, z0], [mid, zm, 'inCubic'], [dur, z1, 'linear']],
                'x': [[0, 360]], 'y': [[0, y(z0)], [mid, y(zm), 'inCubic'], [dur, y(z1), 'linear']], 'move': kind}
    if kind == 'drift_up':                                   # a slow tilt with a small push
        d = round(W * a / 1.04)
        z0 = round(640 / (640 - d / 2) + .005, 4)            # zoomed in enough that the top of a full-frame picture stays out
        z = round(z0 + a * .2, 4)
        return {'zoom': [[0, z0], [dur, z, 'linear']], 'x': [[0, 360]],
                'y': [[0, 640 + d / 2], [mid, round(640 + d / 2 - d * k), 'inCubic'], [dur, 640 - d / 2, 'linear']], 'move': kind}
    # a lateral dolly: the camera slides sideways by a (screen) while zoomed in just enough to keep the frame covered
    d = W * a / 2                                            # each side of the centre, in stage pixels
    z = round(360 / (360 - d) + .008, 4)
    xa, xb = (360 + d, 360 - d) if kind == 'dolly_left' else (360 - d, 360 + d)
    xa, xb = round(xa, 1), round(xb, 1)
    return {'zoom': [[0, z], [dur, round(z + .01, 4), 'linear']],
            'x': [[0, xa], [mid, round(xa + (xb - xa) * k, 1), 'inCubic'], [dur, xb, 'linear']], 'y': [[0, 640]], 'move': kind}


def _speed_change(cam: dict, dur: float, seed) -> dict:
    """An existing move re-timed through a mid-scene keyframe, so it eases into a new speed instead of one flat ramp."""
    z = cam.get('zoom')
    if not isinstance(z, list) or len(z) != 2 or not isinstance(z[0], list): return cam
    r = _rng(f'{seed}|speed')
    mid = round(dur * r.uniform(.45, .6), 2)
    if not z[0][0] < mid < z[-1][0]: return cam
    k = r.choice((.3, .7))
    zm = round(z[0][1] + (z[1][1] - z[0][1]) * k, 4)
    return {**cam, 'zoom': [z[0], [mid, zm, 'inCubic'], [z[1][0], z[1][1], 'linear']]}


def _to_the_cut(cam: dict) -> dict:
    """The camera is still moving when the scene cuts: a last segment that eased to a stop (the default inOutCubic, or
    outCubic) held the picture still for its last second; it runs on at its speed instead."""
    for k in ('zoom', 'x', 'y'):
        v = cam.get(k)
        if isinstance(v, list) and len(v) >= 2 and isinstance(v[-1], list) and v[-1][1] != v[-2][1] \
                and (len(v[-1]) < 3 or v[-1][2] in ('inOutCubic', 'outCubic')):
            cam[k] = v[:-1] + [[v[-1][0], v[-1][1], 'inCubic' if len(v) == 2 else 'linear']]
    return cam


def ensure(sc: dict, dur: float, seed) -> dict:
    """The scene's camera moves at least MIN: a template camera that does less is replaced by a seeded move (one that
    does enough is kept, re-timed half-way when the scene is long), and it is still moving at the cut. Returns the scene."""
    if sc.get('endcard') or sc.get('still_camera'):
        return sc
    if amount(sc, dur) + TOL < MIN:
        sc['camera'] = move(dur, seed)
    elif dur > LONG:
        sc['camera'] = _speed_change(sc['camera'], dur, seed)
    _to_the_cut(sc['camera'])
    return sc


def punch(sc: dict, at: float, dur: float, size: float = .025, settle: float = .4) -> bool:
    """A second picture event: the camera punches in by `size` at `at` (a caption word) and keeps moving from there.
    The zoom is rebuilt as keyframes sampled from the move it had, with the punch multiplied in."""
    cam = sc.get('camera')
    if not cam or not (.6 < at < dur - .6): return False
    zs = cam.get('zoom')
    times = {0.0, round(at, 2), round(at + settle, 2), round(dur, 2)} | {round(i * .5, 2) for i in range(int(dur / .5) + 1)}
    if isinstance(zs, list):
        times |= {round(k[0], 2) for k in zs if isinstance(k, list)}
    times = sorted(times)
    keys = []
    for t in times:
        if t > dur + 1e-9: continue
        base = val(zs, t, 1.0)
        p = min(1.0, max(0.0, (t - at) / settle))
        keys.append([t, round(base * (1 + size * EASE['outCubic'](p)), 4)] + (['outCubic'] if at < t <= at + settle + 1e-9 else ['linear'] if t > 0 else []))
    keys[0] = keys[0][:2]
    cam['zoom'] = keys
    cam['punch'] = round(at, 2)
    return True


def word_punch(sc: dict, words: list, dur: float, seed) -> float | None:
    """For a scene longer than LONG: punch in on a word said between 40 % and 75 % of the scene (the longest word, a
    number first: the word that carries the line). Without a camera move to build on, or a word there, nothing."""
    if dur <= LONG or not sc.get('camera') or sc.get('camera', {}).get('punch') is not None: return None
    cands = [(t, w) for t, w in words if .4 * dur <= t <= .75 * dur]
    if not cands: return None
    r = _rng(f'{seed}|word')
    best = max(cands, key=lambda tw: (any(c.isdigit() for c in tw[1]), len(tw[1]), r.random()))
    return best[0] if punch(sc, best[0], dur) else None



# ====================================================================== shot sizes
H = 1280
FLOOR, CEIL = 1.08, 1.9                # the main move never rests below FLOOR, never closer than CEIL
SIZES = {'wide': (1.08, 1.14), 'medium': (1.28, 1.42), 'close': (1.6, 1.9)}
SOFT = 1.5                             # the engine's layout `soft` limit: a photo shown at most 1.5x its own pixels
RENDER_SCALE = 1.5                     # films are rendered at 1080x1920: 1.5x the 720x1280 stage
DRAWN_MAX = 1.35                       # the motion kit's numbers are a 1080-wide canvas: kept sharp enough
OWN_CAMERA = {'city_zoom', 'map', 'watch_movement'}       # the template's own flight is the move (a map, the 3D movement)
PICTURES = {'image', 'photo', 'cutout', 'reveal'}
MOVE = 0.85                            # seconds a change of shot takes (eased in and out)
LEAD = 0.4                             # it starts this long before the word, so the shot arrives as the word is said
PUSH = 0.012                           # the slow push while a shot holds (zoom per second): a hold never freezes
K = 1.5                                # motion-kit pixels per stage pixel
HUD = 200                              # the screen layer: over the world, under the banner (900) and captions (950)


def _anchor(e, w, h):
    a = str(e.get('anchor') or ('b' if e.get('type') == 'cutout' else 'tl' if e.get('type') == 'kit' else 'c'))
    ax = 0 if 'l' in a else 1 if 'r' in a else .5
    ay = 0 if 't' in a else 1 if 'b' in a else .5
    return ax, ay


def _picture_box(e):
    """(w, h, picture w, picture h, fit) of a picture element as the engine builds it (props.js image/photo, cutout)."""
    ty = e.get('type')
    if ty == 'cutout':
        h = e.get('h', 360); w = e.get('w') or round(h * e.get('aspect', .75))
        return w, h, w, h, 'contain'
    if ty == 'reveal':
        w = e.get('w', 300); h = e.get('h', w)
        return w, h, w, h, 'contain'
    w = e.get('w', 200)
    pol = ty == 'photo' or e.get('polaroid')
    pad = 0 if e.get('frame') is False else (e.get('pad') if e.get('pad') is not None else 14 if pol else 10)
    bottom = (e.get('bottom') or 58) if pol else pad
    h = round((w - pad * 2) / e['aspect'] + pad + bottom) if e.get('aspect') else e.get('h', 200)
    return w, h, w - 2 * pad, h - pad - bottom, e.get('fit') or ('cover' if e.get('aspect') else 'contain')


def _size(e):
    ty = e.get('type')
    if ty in PICTURES:
        return _picture_box(e)[:2]
    if ty == 'text':
        size, text = e.get('size', 90), str(e.get('text', ''))
        w0 = max(1, len(text)) * size * .55                             # one line of it, about
        if not e.get('w'): return w0, size * 1.3
        return min(e['w'], w0), size * 1.3 * max(1, math.ceil(w0 / e['w']))
    if ty == 'stamp':
        size = e.get('size', 46); return len(str(e.get('text', 'DONE'))) * size * .66 + 50, size * 1.55
    if ty == 'kit':
        return W, H
    return e.get('w', 200), e.get('h', 200)


def _scale_at(e, t):
    return val(e.get('scale'), t, 1.0)


def _box(e, t):
    """The element's box on the stage at scene time t (camera not applied): centre x, y, width, height."""
    w, h = _size(e)
    s = _scale_at(e, t)
    x, y = val(e.get('x'), t, 0 if e.get('type') == 'kit' else 360), val(e.get('y'), t, 0 if e.get('type') == 'kit' else 640)
    ax, ay = _anchor(e, w, h)
    return x + (.5 - ax) * w * s, y + (.5 - ay) * h * s, w * s, h * s


def _settle(e):
    i = e.get('in') if isinstance(e.get('in'), dict) else {}
    return float(i.get('at', 0)) + float(i.get('dur', .45)) if i else 0.0


def _texts(e) -> str:
    return ' '.join(str(e.get(k) or '') for k in ('text', 'label', 'title', 'header', 'name'))


def subjects(sc: dict) -> list[dict]:
    """What the camera can frame in a scene, the main subject (hero) first: a picture (the largest; a person framed on
    the face), a number drawn by the motion kit, a card or a stamp, then lines of words. World decor, things pinned to
    the screen (depth 0: credits) and backdrops are never subjects."""
    out = []
    for e in sc.get('elements', []):
        ty = e.get('type')
        if e.get('depth') == 0 or e.get('behind') or e.get('hidden'): continue
        t = _settle(e)
        if ty in PICTURES and (e.get('asset') or e.get('src')) and not e.get('silhouette'):
            cx, cy, w, h = _box(e, t)
            person = isinstance(e.get('idle'), dict) and e['idle'].get('type') == 'breathe'
            out.append({'kind': 'picture', 'cx': cx, 'cy': cy, 'w': w, 'h': h, 'fx': cx, 'fy': cy - h * .33 if person else cy,
                        'person': person, 'text': '', 'area': w * h, 'el': e})
        elif ty == 'svg' and (e.get('print') or (isinstance(e.get('idle'), dict) and e['idle'].get('type') == 'breathe')):
            cx, cy, w, h = _box(e, t)                                    # a print in the world, or a drawn person
            person = not e.get('print')
            out.append({'kind': 'picture', 'cx': cx, 'cy': cy, 'w': w, 'h': h, 'fx': cx, 'fy': cy - h * .33 if person else cy,
                        'person': person, 'text': '', 'area': w * h * .9, 'el': e})
        elif ty == 'kit':
            for d in e.get('draw') or []:
                if 'cx' in d and 'cy' in d:                              # a number: odometer, counter
                    txt = f"{d.get('prefix', '')}{d.get('val', '')}{d.get('suffix', '')}"
                    size = d.get('size', 160) / K
                    w = max(size, len(str(txt)) * size * .6)
                    out.append({'kind': 'chart', 'cx': d['cx'] / K, 'cy': d['cy'] / K, 'w': w, 'h': size * 1.1, 'fx': d['cx'] / K,
                                'fy': d['cy'] / K, 'text': str(d.get('val', '')), 'area': w * size * 2, 'el': e})
                elif isinstance(d.get('box'), dict):                     # a chart, an icon array
                    b = d['box']
                    out.append({'kind': 'chart', 'cx': (b['x'] + b['w'] / 2) / K, 'cy': (b['y'] + b['h'] / 2) / K, 'w': b['w'] / K,
                                'h': b['h'] / K, 'fx': (b['x'] + b['w'] / 2) / K, 'fy': (b['y'] + b['h'] / 2) / K, 'text': '',
                                'area': b['w'] * b['h'] / K / K, 'el': e})
        elif ty in ('card', 'stamp') or (ty == 'text' and not e.get('still')):
            cx, cy, w, h = _box(e, t)
            if w < 20 or h < 14: continue
            out.append({'kind': 'card' if ty != 'text' else 'text', 'cx': cx, 'cy': cy, 'w': w, 'h': h, 'fx': cx, 'fy': cy,
                        'text': _texts(e), 'area': w * h * (.6 if ty == 'text' else .8), 'el': e})
    rank = {'picture': 0, 'chart': 1, 'card': 2, 'text': 3}
    out.sort(key=lambda s: (rank[s['kind']], -s['area']))
    return out


def hero(sc: dict) -> dict | None:
    s = subjects(sc)
    return s[0] if s else None


def _natural_factor(e, nw, nh) -> float:
    """Stage pixels per pixel of the picture's file, as the engine fits it in its box."""
    _, _, bw, bh, fit = _picture_box(e)
    return max(bw / nw, bh / nh) if fit == 'cover' else min(bw / nw, bh / nh)


def cap(sc: dict, pixels: dict | None, scale: float = RENDER_SCALE, soft: float = SOFT, dur: float | None = None) -> float:
    """The closest the camera may come without showing any photo bigger than its pixels allow: each picture's own size
    (`pixels`: {asset or file stem: (w, h)}), its box, its own scale keys and its depth, at the render scale. A drawn
    canvas (the motion kit) is capped at DRAWN_MAX. Never more than CEIL."""
    out = CEIL
    dur = dur or sc.get('dur') or 6.0
    for e in sc.get('elements', []):
        if e.get('depth') == 0: continue
        d = float(e.get('depth', 1) or 1)
        if e.get('type') == 'kit':
            out = min(out, DRAWN_MAX); continue
        if e.get('type') not in PICTURES or not pixels: continue
        name = e.get('asset') or Path(str(e.get('src') or '')).stem
        if name not in pixels: continue
        nw, nh = pixels[name]
        es = max(_scale_at(e, dur * i / 12) for i in range(13))
        k = _natural_factor(e, nw, nh) * es * scale                     # output pixels per pixel of the file, camera at 1
        out = min(out, 1 + (soft / k - 1) / d)
    return round(max(1.0, out), 3)


def pixels(assets: Path) -> dict:
    """{file stem: (width, height)} of every picture in a film's assets folder (for `cap`)."""
    from PIL import Image
    out = {}
    for f in Path(assets).glob('*'):
        if f.suffix.lower() not in ('.jpg', '.jpeg', '.png', '.webp'): continue
        try:
            with Image.open(f) as im: out[f.stem] = im.size
        except OSError:
            continue
    return out


def frame(z: float, fx: float, fy: float) -> tuple[float, float]:
    """The camera point that puts (fx, fy) in the middle of the frame at zoom z, moved only as far as needed to keep
    the world's edge out of the frame (Bang Motion's frameOn with its clamp)."""
    hx, hy = W / 2 / z, H / 2 / z
    return round(min(max(fx, hx), W - hx), 1), round(min(max(fy, hy), H - hy), 1)


def _word_at(shot: dict):
    return next((shot[k] for k in ('on', True, 'word') if shot.get(k) is not None), None)


def _when(shot: dict, words) -> float | None:
    from .checks import stem, words as split
    if shot.get('at') is not None:
        return float(shot['at'])
    on = _word_at(shot)
    want = split(str(on)) if on is not None else []
    if not want: return None
    hits = [t for t, w in words if w == want[0] or stem(w) == stem(want[0])]
    n = int(shot.get('nth', 1))
    return float(hits[n - 1]) if len(hits) >= n else None


def _named(word: str, targets: list[dict]) -> dict | None:
    """The on-screen thing a spoken word names: a line of words, a card or a number that contains it."""
    from .checks import stem, words as split
    st = stem(word)
    if len(st) < 3 and not word.isdigit(): return None
    for tg in targets:
        if tg['kind'] == 'picture' or not tg['text']: continue
        ws = split(tg['text'].replace(',', ''))
        if any(w == word or stem(w) == st or (word.isdigit() and w.replace(',', '') == word.replace(',', '')) for w in ws):
            return tg
    return None


def _union(a: dict, b: dict) -> dict:
    x0, x1 = min(a['cx'] - a['w'] / 2, b['cx'] - b['w'] / 2), max(a['cx'] + a['w'] / 2, b['cx'] + b['w'] / 2)
    y0, y1 = min(a['cy'] - a['h'] / 2, b['cy'] - b['h'] / 2), max(a['cy'] + a['h'] / 2, b['cy'] + b['h'] / 2)
    return {**a, 'kind': 'card', 'cx': (x0 + x1) / 2, 'cy': (y0 + y1) / 2, 'w': x1 - x0, 'h': y1 - y0, 'fx': (x0 + x1) / 2, 'fy': (y0 + y1) / 2}


def _zoom(size, tg: dict, r: random.Random, top: float) -> float:
    if isinstance(size, (int, float)) and not isinstance(size, bool):
        z = float(size)
    else:
        lo, hi = SIZES.get(str(size), SIZES['medium'])
        z = r.uniform(lo, hi)
    if top < CEIL:                                                   # a capped camera keeps its shot sizes apart, closer
        room = max(0.0, top / (1 + PUSH * 3) - FLOOR)                # together, and room for the slow push at the top
        z = FLOOR + (z - FLOOR) * room / (CEIL - FLOOR) if z > FLOOR else z
    if tg['kind'] in ('text', 'card', 'chart') and tg.get('w'):     # words and numbers stay whole in the frame
        z = min(z, .9 * W / max(1.0, tg['w']), .9 * H / max(1.0, tg['h']))
    return round(max(min(FLOOR, top), min(z, CEIL, top)), 4)


def _focus(size, tg: dict) -> tuple[float, float]:
    if size == 'wide' and tg['kind'] != 'point':                     # a wide shot keeps the whole composition
        return 360 + (tg['fx'] - 360) * .5, 640 + (tg['fy'] - 640) * .5
    return tg['fx'], tg['fy']


def _size_of(z: float) -> str:
    return 'close' if z >= SIZES['close'][0] - .05 else 'medium' if z >= SIZES['medium'][0] - .05 else 'wide'


def plan(sc: dict, dur: float, seed, words=(), shots=None, top: float = CEIL) -> list[dict]:
    """The scene's shots: [{at, size, z, fx, fy, tg}], the first at 0. From the line's own `shots:` when it has them,
    else seeded: wide -> close-up on the word that carries the line (or born close, pulling back on it), and a third
    shot in a long scene. Never the same size twice in a row."""
    r = _rng(f'{seed}|shots')
    targets = subjects(sc)
    centre = {'kind': 'point', 'cx': 360, 'cy': 640, 'w': 0, 'h': 0, 'fx': 360, 'fy': 640, 'text': ''}
    lead = targets[0] if targets else centre
    words = [(float(t), str(w)) for t, w in (words or [])]

    def tgt_for(word):
        tg = _named(word, targets) if word else None
        if tg and lead is not tg and lead['kind'] in ('picture', 'chart') and tg['kind'] == 'text' and abs(tg['cy'] - lead['cy']) < 200:
            tg = _union(lead, tg)                                    # «دينار» under the number: the price, number and unit
        return tg or lead

    def shot(t, size, tg):
        z = _zoom(size, tg, r, top)
        fx, fy = _focus(size, tg)
        return {'at': round(t, 2), 'size': size if isinstance(size, str) else _size_of(z), 'z': z, 'fx': round(fx, 1), 'fy': round(fy, 1), 'tg': tg}

    if shots:
        evs = []
        for sh in shots:
            sh = {'to': sh} if isinstance(sh, str) else dict(sh)
            t = _when(sh, words)
            if t is None or not 0 <= t < dur - .3: continue
            word = _word_at(sh)
            tg = ({'kind': 'point', 'cx': sh['focus'][0], 'cy': sh['focus'][1], 'w': 0, 'h': 0, 'fx': float(sh['focus'][0]),
                   'fy': float(sh['focus'][1]), 'text': ''} if sh.get('focus') else tgt_for(str(word) if word is not None else ''))
            evs.append(shot(t, sh.get('to', 'close'), tg))
        evs.sort(key=lambda e: e['at'])
        if evs and evs[0]['at'] <= .05:                                  # the line asks for its opening shot itself
            return evs
        return [shot(0, 'medium' if evs and evs[0]['size'] == 'wide' else 'wide', lead)] + evs
    # seeded: the word that carries the line (a number first, then a word the screen shows, then the longest)
    def key(lo, hi):
        c = [(t, w) for t, w in words if lo * dur <= t <= hi * dur and .9 <= t <= dur - 1.3]
        if not c: return None
        return max(c, key=lambda tw: (any(ch.isdigit() for ch in tw[1]), _named(tw[1], targets) is not None, len(tw[1]), r.random()))
    pattern = r.choice(('in', 'in', 'out'))
    if lead.get('person'): pattern = 'face'                          # the owner: a person is met face first, then the place
    k1 = key(.25, .7) or ((round(dur * r.uniform(.35, .5), 2), '') if dur > 2.4 else None)
    if pattern == 'in':
        out = [shot(0, 'wide', lead)]
        if k1: out.append(shot(k1[0], 'close', tgt_for(k1[1])))
    elif pattern == 'face':                                              # close on the face, then pull back to the whole scene
        out = [shot(0, 'close', lead)]
        out.append(shot(k1[0] if k1 else round(min(dur * .45, 2.4), 2), 'wide', lead))
    else:
        out = [shot(0, 'close', lead)]
        if k1: out.append(shot(k1[0], r.choice(('wide', 'medium')), tgt_for(k1[1])))
    if dur > 7.0 and k1:
        k2 = key(.62, .9)
        if k2 and k2[0] - k1[0] > MOVE + 1.0:
            last = out[-1]['size']
            out.append(shot(k2[0], 'medium' if last != 'medium' else r.choice(('close', 'wide')), tgt_for(k2[1])))
    return out


def _keys(events: list[dict], dur: float, top: float) -> dict:
    zk, xk, yk = [], [], []

    def put(t, z, fx, fy, ease=None):
        z = round(min(z, max(top, 1.0)), 4)
        x, y = frame(z, fx, fy)
        for ks, v in ((zk, z), (xk, x), (yk, y)):
            ks.append([round(t, 2), v] + ([ease] if ease else []))

    e0 = events[0]
    z, fx, fy, last = e0['z'], e0['fx'], e0['fy'], 0.0
    put(0, z, fx, fy)
    done = [e0]
    for e in events[1:]:
        t0 = max(last + .35, e['at'] - LEAD)
        t1 = t0 + MOVE
        if t1 > dur - .25: break
        put(t0, z * (1 + PUSH * (t0 - last)), fx, fy, 'linear')
        put(t1, e['z'], e['fx'], e['fy'], 'inOutCubic')
        z, fx, fy, last = e['z'], e['fx'], e['fy'], t1
        done.append(e)
    put(dur, z * (1 + PUSH * (dur - last)), fx, fy, 'linear')
    cam = {'zoom': zk, 'x': xk, 'y': yk, 'clamp': True, 'move': 'shots',
           'shots': [{'at': e['at'], 'size': e['size'], 'zoom': e['z'], 'focus': [e['fx'], e['fy']]} for e in done]}
    for k, e in (('start', done[0]), ('end', done[-1])):
        cam[k] = {'focus': [e['fx'], e['fy']], 'w': round(e['tg'].get('w') or 0, 1)}
    return cam


def direct(sc: dict, dur: float, seed, words=(), shots=None, pixels: dict | None = None, template: str | None = None) -> dict:
    """The scene's camera as shot sizes on its words (see the module notes). The template's own picture zoom (a Ken
    Burns on the photo) is folded into the camera, so one move carries the scene; a backdrop photo sits a little behind
    (depth 0.4, a parallax) so the camera can come close to the words in front of it. A template that flies its own
    camera (a map, a city zoom, the 3D movement) keeps it. Returns the scene."""
    if sc.get('endcard') or sc.get('still_camera'): return sc
    if template in OWN_CAMERA:
        sc.setdefault('camera', {})['own'] = template
        return sc
    tgs = subjects(sc)
    lead = tgs[0] if tgs else None
    for e in sc.get('elements', []):
        if e.get('behind') and e.get('type') in PICTURES and e.get('depth') is None:
            e['depth'] = .4
        # a picture's label, card and words sit on the screen, not in the world (Bang Motion's HUD layer): the shot
        # comes close to the photo while its words stay where they are read, clear of the captions
        if lead and lead['kind'] == 'picture' and e.get('type') in CONTENT and e.get('depth') is None and not e.get('behind'):
            e['depth'] = 0
            e['z'] = HUD + (e.get('z') or 0)                         # over the photo however close the camera comes
    if lead and lead['kind'] == 'picture':
        el = lead['el']
        sk, xk, yk = el.get('scale'), el.get('x'), el.get('y')
        steady = lambda k: not isinstance(k, list) or len({str(v[1]) for v in k if isinstance(v, list)}) <= 1
        if isinstance(sk, list) and sk and isinstance(sk[0], list) and steady(xk) and steady(yk):
            el['scale'] = min(v[1] for v in sk)
    top = cap(sc, pixels, dur=dur)
    events = plan(sc, dur, seed, words=words, shots=shots, top=top)
    cam = _keys(events, dur, top)
    if top < CEIL: cam['cap'] = top
    sc['camera'] = cam
    return sc


def screen_point(sc: dict, t: float, fx: float, fy: float) -> tuple[float, float, float]:
    """Where a stage point is on screen at scene time t under the scene's camera (clamped as the engine clamps): x, y, zoom."""
    cam = sc.get('camera') or {}
    z = max(1.0, val(cam.get('zoom'), t, 1.0))
    x, y = val(cam.get('x'), t, 360), val(cam.get('y'), t, 640)
    if cam.get('clamp'): x, y = (min(max(x, W / 2 / z), W - W / 2 / z), min(max(y, H / 2 / z), H - H / 2 / z))
    return 360 + (fx - x) * z, 640 + (fy - y) * z, z


def cut_focus(sc: dict) -> list[float]:
    """Where the scene is born on screen (its first subject at t = 0): the push-through dives toward it."""
    st = (sc.get('camera') or {}).get('start')
    if not st: return [360.0, 640.0]
    x, y, _ = screen_point(sc, 0, *st['focus'])
    return [round(min(max(x, 40), W - 40), 1), round(min(max(y, 80), H - 80), 1)]


def match(a: dict, b: dict) -> bool:
    """A match cut: B's first frame is set so its subject sits where A's last subject is on screen, at the same size;
    B's camera then settles into its own first shot. Returns whether both had a subject to line up."""
    ea, sb_ = (a.get('camera') or {}).get('end'), (b.get('camera') or {}).get('start')
    cb = b.get('camera') or {}
    if not ea or not sb_ or not isinstance(cb.get('zoom'), list): return False
    sx, sy, za = screen_point(a, a['dur'], *ea['focus'])
    wa = (ea['w'] or 0) * za
    top = cb.get('cap', CEIL)
    zb = wa / sb_['w'] if sb_['w'] and wa else cb['zoom'][0][1]
    zb = round(max(min(FLOOR, top), min(zb, CEIL, top)), 4)
    fx, fy = sb_['focus']
    x, y = frame(zb, fx - (sx - 360) / zb, fy - (sy - 640) / zb)
    k0 = [cb[k][0][1] for k in ('zoom', 'x', 'y')]
    cb['zoom'][0][1], cb['x'][0][1], cb['y'][0][1] = zb, x, y
    nxt = cb['zoom'][1][0] if len(cb['zoom']) > 1 else b['dur']
    ts = round(min(1.0, nxt * .6), 2)                                # it settles into its own first shot in a second
    if nxt - ts > .1:
        for k, v in zip(('zoom', 'x', 'y'), k0):
            cb[k].insert(1, [ts, v, 'outCubic'])
    cb['matched'] = [round(sx, 1), round(sy, 1)]
    return True


# ====================================================================== entrances and exits
CONTENT = {'text', 'card', 'stamp'}
GLIDE = {'rise': 'flyU', 'slideL': 'flyL', 'slideR': 'flyR'}


def choreograph(sc: dict, dur: float, leaving: bool, rtl: bool = True) -> dict:
    """Asymmetric, overlapping entrances and exits for the scene's words, cards and stamps (Bang Motion's rule): they
    glide in for 0.85 s and settle hard (the engine's fly* types), and, before the cut to another scene, leave in 0.38 s
    one after another, accelerating toward the next page (to the right in an Arabic film) while the camera carries on.
    The engine blurs them along their travel while they move fast. Returns the scene."""
    k = 0
    for e in sc.get('elements', []):
        if e.get('type') not in CONTENT or e.get('depth') == 0 or e.get('behind') or e.get('still'): continue
        inn = e.get('in')
        if isinstance(inn, dict) and inn.get('type') in GLIDE:
            e['in'] = {**inn, 'type': GLIDE[inn['type']], 'dur': max(.85, float(inn.get('dur', .45)))}
        if leaving and not e.get('out'):
            at = round(dur - .5 + .06 * k, 2)
            if at > _settle(e) + .8:
                e['out'] = {'type': 'flyR' if rtl else 'flyL', 'at': at, 'dur': .38, 'from': 240}
                k += 1
    return sc


# ====================================================================== the stage law
MOVERS = 8                              # things that move in a scene, world decor counted (a set gives 8-60)
_ANIMATED = {'kit', 'sparkles', 'movement3d', 'map', 'reveal', 'spotlight'}
_KEYS = ('x', 'y', 'scale', 'rot', 'opacity', 'view', 'reveal')


def moving(e: dict) -> bool:
    """Whether an element moves during its scene: an entrance, an exit, an idle, keys that change, or its own animation."""
    if e.get('in') or e.get('out') or e.get('idle'): return True
    if e.get('type') in _ANIMATED: return True
    for k in _KEYS:
        v = e.get(k)
        if isinstance(v, list) and v and isinstance(v[0], list) and len({str(x[1]) for x in v}) > 1: return True
    return False


def top_zoom(sc: dict, dur: float) -> float:
    z = (sc.get('camera') or {}).get('zoom')
    return max(val(z, dur * i / 40, 1.0) for i in range(41))


def stage_law(sb: dict, least: int = MOVERS) -> list[dict]:
    """The anti-slide checks (Bang Motion's stage law, for our scenes): fewer than `least` moving things, a main camera
    move that never reaches FLOOR (a few % reads as a still), and a plain fade (or slide) inside one place, where the
    camera should carry the cut. [{code, scene, t, dur, say, fix}]"""
    out, t, prev = [], 0.0, None
    for i, s in enumerate(sb.get('scenes', [])):
        d = float(s.get('dur') or 0)
        if not s.get('endcard'):
            n = sum(map(moving, s.get('elements', [])))
            if n < least:
                out.append({'code': 'FEW_MOVERS', 'scene': i, 't': t, 'dur': d, 'say': f'only {n} things move (at least {least}, its world counted)',
                            'fix': 'give the line a world (set:) or more moving pieces'})
            cam = s.get('camera') or {}
            if not cam.get('own') and not s.get('still_camera'):
                z = top_zoom(s, d)
                if z + TOL < FLOOR:
                    held = cam.get('cap') is not None and cam['cap'] < FLOOR
                    out.append({'code': 'CAMERA_FLOOR', 'scene': i, 't': t, 'dur': d,
                                'say': f'the main camera move reaches zoom {z:.2f} (at least {FLOOR})' + (f", held there by the photo's resolution" if held else ''),
                                'fix': 'a larger scan of the photo, or show it as a print' if held else 'a shot-size move: wide, medium, close-up (motion.direct)'})
            if prev is not None and s.get('transition') in ('fade', 'slide') and s.get('set') and s.get('set') == prev.get('set'):
                out.append({'code': 'FADE_SAME_PLACE', 'scene': i, 't': t, 'dur': d,
                            'say': f"a plain {s['transition']} between two scenes in the same place ({s['set']})",
                            'fix': 'let the camera carry the cut: cut: push or cut: match'})
        prev = s
        t += d
    return out
