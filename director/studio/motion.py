"""The camera of every scene: a real move, measured.

Étienne's review of Halter measured a film whose camera hardly moved: paper_cutout pushed 1.00 -> 1.02 over 10-12 s,
and the photo scenes stood at 1.00. The rule since then (storytelling rule 18d):
  * every scene's camera moves at least MIN (3 %): a push-in, a pull-back, a drift or a lateral dolly, chosen by the
    scene's seed so neighbouring scenes do not all move the same way;
  * a scene longer than LONG (5 s) gets a second picture event: a punch-in on a caption word (quickfilm, which knows
    when each word is said), or at least a change of speed half-way, so the picture never settles into a hold.
`amount()` is the measure the review and quality steps use (LONG_HOLD): the larger of how far the zoom travels and how
far the picture pans (screen pixels, against the 720-wide frame) over the scene, sampled as the engine plays the keys.
"""
from __future__ import annotations
import hashlib, math, random

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
