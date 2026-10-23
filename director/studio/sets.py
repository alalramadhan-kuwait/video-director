"""Story worlds: set dressing and a sound bed that put a scene in the place the story is happening.

A set is drawn behind (and a little in front of) any catalogue template: under the sea, a night sea with a warship,
Florence's skyline, a watchmaker's bench, a radium lab, an archive desk. It moves with the camera (depth), loops its
ambience under the voice and never covers the words: content keeps the middle of the frame, decor keeps to the back,
the edges and the bottom. Everything is drawn in code (paper style, the brand's muted tones); nothing is generated.
    sc = art.scene_visual(...); sets.dress(sc, 'underwater', dur)
"""
from __future__ import annotations
import itertools, math, random

_IDS = itertools.count(1)


def uid(name: str) -> str:
    """A gradient id no other scene uses: every scene's SVGs share one page, and a repeated id makes a later scene
    point at an earlier (hidden) scene's gradient, which then draws nothing."""
    return f'{name}{next(_IDS)}'

W, H = 760, 1320                       # a little larger than the 720x1280 frame, so camera moves never show an edge


def _svg(w, h, body):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{body}</svg>'


def _el(svg_body, w=W, h=H, x=360, y=640, **kw):
    return {'type': 'svg', 'w': w, 'h': h, 'svg': _svg(w, h, svg_body), 'x': x, 'y': y, 'anchor': 'c', 'still': True, **kw}


def _backdrop(top, bottom):          # first in the list, so the engine draws it under the rest of the decor
    i = uid('bd')
    g = (f'<defs><linearGradient id="{i}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{top}"/>'
         f'<stop offset="1" stop-color="{bottom}"/></linearGradient></defs><rect width="{W}" height="{H}" fill="url(#{i})"/>')
    return _el(g, behind=True, depth=0)


def _motes(rng, n, color, dur, y0=150, y1=1150, rise=60, r=(1.5, 3.5), op=.35, depth=(.5, .9), behind=True):
    out = []
    for _ in range(n):
        rr = rng.uniform(*r); x, y = rng.uniform(20, 700), rng.uniform(y0, y1)
        out.append(_el(f'<circle cx="{rr * 2}" cy="{rr * 2}" r="{rr}" fill="{color}"/>', rr * 4, rr * 4, x, [[0, y], [dur, y - rise]],
                       opacity=round(op * rng.uniform(.5, 1), 2), depth=round(rng.uniform(*depth), 2), behind=behind,
                       idle={'type': 'float', 'amp': rng.uniform(3, 8), 'speed': rng.uniform(.2, .5), 'phase': rng.uniform(0, 6)}))
    return out


def _gear(r, teeth, color, hole=.35):
    pts = []
    for i in range(teeth * 2):
        a = math.pi * i / teeth; rr = r if i % 2 == 0 else r * .82
        for da in (-.32, .32):
            pts.append(f'{r + rr * math.cos(a + da * math.pi / teeth):.1f},{r + rr * math.sin(a + da * math.pi / teeth):.1f}')
    return (f'<polygon points="{" ".join(pts)}" fill="{color}"/><circle cx="{r}" cy="{r}" r="{r * hole}" fill="#000" fill-opacity=".55"/>')


# ---------------------------------------------------------------------------------------------------------- the worlds
def underwater(dur, rng):
    els = [_backdrop('#2A4A57', '#060B0E')]
    for i, (x, w, op) in enumerate(((180, 120, .16), (380, 90, .12), (560, 140, .14), (290, 60, .10), (470, 50, .09))):     # light from the surface
        ray = f'<polygon points="{x - w / 2},0 {x + w / 2},0 {x + w * 1.6},{H} {x - w * 1.1},{H}" fill="#DCE8EC" fill-opacity="{op}"/>'
        els.append(_el(ray, behind=True, depth=.3, opacity=[[0, .6], [dur * .5, 1], [dur, .7]],
                       idle={'type': 'sway', 'amp': 1.2, 'speed': .15 + .05 * i, 'phase': i}))
    els += _motes(rng, 28, '#A9BEC6', dur, rise=50)
    for i in range(24):                                                     # bubbles rising past the frame
        r = rng.uniform(5, 14); s = rng.uniform(-2, dur - 1); span = rng.uniform(3.5, 6)
        x = rng.choice([rng.uniform(30, 150), rng.uniform(570, 690), rng.uniform(150, 570)])
        b = (f'<circle cx="{r + 1}" cy="{r + 1}" r="{r}" fill="#CFE0E6" fill-opacity=".12" stroke="#E4F0F3" stroke-opacity=".6" stroke-width="1.5"/>'
             f'<circle cx="{r * .6 + 1}" cy="{r * .6 + 1}" r="{r * .25}" fill="#FFFFFF" fill-opacity=".7"/>')
        els.append(_el(b, 2 * r + 2, 2 * r + 2, x, [[max(0, s), 1360 - max(0, -s) * 1400 / span], [s + span, -60]],
                       depth=1.1, behind=x > 150 and x < 570, idle={'type': 'sway', 'amp': 6, 'speed': .8, 'phase': i}))
    weed = ('<path d="M40 420 C 10 330, 70 260, 30 170 C 0 100, 50 50, 30 0 L 48 0 C 70 60, 25 110, 55 175 C 92 260, 35 330, 70 420 Z" fill="#1D343D"/>'
            '<path d="M95 420 C 80 350, 130 300, 100 230 C 80 180, 120 140, 105 90 L 120 90 C 140 150, 100 190, 120 235 C 150 305, 105 350, 120 420 Z" fill="#24414B"/>')
    for x, body in ((70, weed), (650, f'<g transform="translate(160 0) scale(-1 1)">{weed}</g>')):    # the right one mirrored
        els.append({**_el(body, 160, 420, x, 1140), 'depth': 1.25, 'crop': True, 'underCaptions': True,
                    'idle': {'type': 'sway', 'amp': 3, 'speed': .35, 'phase': 1 if x < 360 else 2.5}})
    return {'theme': 'tk-ink', 'elements': els, 'beds': [('underwater', -22)], 'sfx': [(0.5, 'bubbles', -18), (dur * .6, 'bubbles', -22)]}


def sea_night(dur, rng):
    els = [_backdrop('#2B3038', '#15171B')]
    for _ in range(24):
        x, y, r = rng.uniform(20, 700), rng.uniform(60, 520), rng.uniform(1, 2.4)
        a = rng.uniform(0, dur)
        els.append(_el(f'<circle cx="3" cy="3" r="{r}" fill="#F3F0E8"/>', 6, 6, x, y, behind=True, depth=.2,
                       opacity=[[0, .3], [a, .9], [min(dur, a + 1.2), .3]]))
    els.append({'type': 'moon', 'x': 560, 'y': 300, 'size': 110, 'color': '#E4DFD3', 'depth': .3, 'behind': True})
    ship = ('<path d="M0 70 L30 92 L330 92 L360 70 Z" fill="#101214"/><rect x="70" y="52" width="190" height="18" fill="#101214"/>'
            '<rect x="120" y="30" width="70" height="22" fill="#101214"/><rect x="150" y="0" width="6" height="30" fill="#101214"/>'
            '<rect x="205" y="38" width="16" height="14" fill="#101214"/><rect x="230" y="44" width="70" height="4" fill="#101214"/>'
            '<rect x="40" y="62" width="40" height="4" fill="#101214"/>')
    els.append(_el(ship, 360, 92, [[0, 820], [dur, 560]], 790, behind=True, depth=.5))           # a warship crossing the horizon
    from .art import _waves
    for k, (d, col, depth) in enumerate(_waves('#0F1013', '#1B1D22', '#2A2D33')):
        els.append({'type': 'svg', 'w': 900, 'h': 600, 'x': [[0, 360 + 25 * (k + 1)], [dur, 360 - 25 * (k + 1)]], 'y': 1010 + k * 50,
                    'svg': _svg(900, 600, f'<path d="{d}" fill="{col}"/>'), 'depth': depth, 'behind': True, 'still': True,
                    'idle': {'type': 'bob', 'amp': 4 + 2 * k, 'speed': .5 + .2 * k}})
    fog = f'<rect width="{W}" height="140" fill="#C9C3B4" fill-opacity=".06"/>'
    els.append(_el(fog, W, 140, [[0, 320], [dur, 400]], 760, behind=True, depth=.4))
    return {'theme': 'tk-graphite', 'elements': els, 'beds': [('sea', -22), ('wind', -32)], 'sfx': []}


def florence(dur, rng):
    els = [_backdrop('#E8D3AE', '#E4DFD3')]
    far = ('<path d="M0 300 L0 210 L60 210 L60 190 L110 190 L110 215 L170 215 L170 200 L230 200 L230 300 Z" fill="#CBC3B1"/>'
           '<path d="M480 300 L480 205 L540 205 L540 185 L600 185 L600 210 L680 210 L680 195 L760 195 L760 300 Z" fill="#CBC3B1"/>')
    near = (  # Palazzo Vecchio's tower, the cathedral dome with its lantern, Giotto's bell tower, roofs and cypresses
        '<rect x="120" y="70" width="34" height="200" fill="#B3AB98"/><rect x="112" y="60" width="50" height="16" fill="#B3AB98"/>'
        '<rect x="130" y="30" width="14" height="32" fill="#B3AB98"/><rect x="80" y="170" width="130" height="130" fill="#B3AB98"/>'
        '<path d="M300 300 L300 205 Q 300 95 380 85 Q 460 95 460 205 L460 300 Z" fill="#A79F8B"/><rect x="368" y="52" width="24" height="36" fill="#A79F8B"/>'
        '<path d="M368 52 L380 30 L392 52 Z" fill="#A79F8B"/><rect x="250" y="200" width="260" height="100" fill="#A79F8B"/>'
        '<rect x="530" y="60" width="44" height="240" fill="#B3AB98"/><rect x="526" y="52" width="52" height="10" fill="#B3AB98"/>'
        '<path d="M0 300 L0 240 L50 225 L90 245 L90 300 Z M600 300 L600 235 L660 220 L720 240 L760 232 L760 300 Z" fill="#A79F8B"/>'
        '<ellipse cx="225" cy="230" rx="11" ry="58" fill="#8F877A"/><ellipse cx="640" cy="225" rx="12" ry="64" fill="#8F877A"/>'
        '<ellipse cx="668" cy="242" rx="9" ry="48" fill="#8F877A"/>')
    els.append({**_el(far, W, 300, 360, 1010, depth=.5, crop=True, underCaptions=True), 'scale': 1.35})
    els.append({**_el(near, W, 300, 360, 1080, depth=.8, crop=True, underCaptions=True), 'scale': 1.35})
    for i in range(5):                                                      # swallows over the roofs
        x0 = rng.uniform(-80, 100); y = rng.uniform(260, 420)
        bird = '<path d="M0 6 Q 7 0 14 6 Q 21 0 28 6" stroke="#6E675C" stroke-width="2.4" fill="none"/>'
        els.append(_el(bird, 28, 10, [[0, x0 + i * 40], [dur, x0 + i * 40 + 260]], [[0, y], [dur, y - 40]], behind=True, depth=.35,
                       idle={'type': 'bob', 'amp': 6, 'speed': 1.2, 'phase': i}))
    return {'theme': 'tk-bone', 'elements': els, 'beds': [('crowd', -36)], 'sfx': [(0.4, 'bell_far', -16)]}


def workshop(dur, rng):
    els = [_backdrop('#1E2024', '#0B0C0E'),
           {'type': 'spotlight', 'x': 360, 'y': 560, 'w': 720, 'h': 1000, 'opacity': .45, 'behind': True}]
    for x, y, r, teeth, turn, op in ((70, 260, 110, 16, 1, .22), (660, 1080, 140, 20, -1, .2), (610, 300, 60, 12, -1, .18), (110, 1120, 70, 12, 1, .16)):
        els.append({**_el(_gear(r, teeth, '#8A857A'), 2 * r, 2 * r, x, y), 'opacity': op, 'depth': .7, 'behind': True,
                    'rot': [[0, 0], [dur, turn * 360 * dur / (r / 6)]]})
    els += _motes(rng, 22, '#E9E2CF', dur, y0=250, y1=900, rise=40, op=.45)
    return {'theme': 'tk-ink', 'elements': els, 'beds': [('watch_run', -28), ('room', -34)], 'sfx': []}


def radium(dur, rng):
    els = [_backdrop('#0B0D0C', '#030403')]
    for x, y, s in ((130, 1050, 230), (600, 1000, 260), (360, 240, 300)):
        i = uid('glow')
        glow = f'<defs><radialGradient id="{i}"><stop offset="0" stop-color="#9FD9A3" stop-opacity=".55"/><stop offset="1" stop-color="#9FD9A3" stop-opacity="0"/></radialGradient></defs>'
        els.append({**_el(glow + f'<circle cx="{s / 2}" cy="{s / 2}" r="{s / 2}" fill="url(#{i})"/>', s, s, x, y), 'behind': True, 'depth': .5,
                    'opacity': [[0, .5], [dur * .5, .9], [dur, .6]]})
    vial = ('<rect x="14" y="0" width="28" height="12" rx="3" fill="#5A5E5A"/><path d="M10 12 L46 12 L46 120 Q46 140 28 140 Q10 140 10 120 Z" '
            'fill="#1C221D" stroke="#7E8A80" stroke-width="2"/><path d="M12 80 L44 80 L44 120 Q44 138 28 138 Q12 138 12 120 Z" fill="#9FD9A3" fill-opacity=".75"/>')
    for x, y in ((110, 1080), (170, 1100), (610, 1060)):
        els.append({**_el(vial, 56, 142, x, y), 'depth': 1.1, 'crop': True, 'underCaptions': True})
    els += _motes(rng, 30, '#B8EBBB', dur, rise=30, op=.6, r=(1.2, 2.8))
    return {'theme': 'tk-black', 'elements': els, 'beds': [('geiger', -26)], 'sfx': []}


def archive(dur, rng):
    els = []
    for i in range(5):
        x, y, rot = rng.uniform(80, 640), rng.uniform(200, 1100), rng.uniform(-14, 14)
        lines = ''.join(f'<rect x="24" y="{40 + k * 22}" width="{rng.uniform(120, 220):.0f}" height="5" fill="#9C9483" fill-opacity=".5"/>' for k in range(9))
        els.append({**_el(f'<rect width="260" height="320" fill="#EFEBE1"/>{lines}', 260, 320, x, y), 'rot': rot, 'opacity': .55,
                    'behind': True, 'depth': .6})
    ring = '<circle cx="70" cy="70" r="58" fill="none" stroke="#8C6F4E" stroke-opacity=".35" stroke-width="7"/>'
    els.append({**_el(ring, 140, 140, 600, 1020), 'behind': True, 'depth': .6})
    els += _motes(rng, 14, '#FFFFFF', dur, rise=20, op=.5)
    return {'theme': 'tk-linen', 'elements': els, 'beds': [('room', -32)], 'sfx': []}


SETS = {'underwater': underwater, 'sea_night': sea_night, 'florence': florence, 'workshop': workshop, 'radium': radium, 'archive': archive}
NAME_AR = {'underwater': 'تحت الماء', 'sea_night': 'بحر ليلي وسفينة', 'florence': 'فلورنسا', 'workshop': 'ورشة الساعاتي',
           'radium': 'مختبر الراديوم', 'archive': 'مكتب الأرشيف'}


def theme_for(set_id: str | None, default: str) -> str:
    if not set_id: return default
    return SETS[set_id](1.0, random.Random(0))['theme']


def dress(sc: dict, set_id: str | None, dur: float, seed: str = '', template: str | None = None) -> dict:
    """Add the world behind the scene's own elements, its ambience as looping beds, and its one-off sounds. A template
    that fills the frame (a map, a full photo) is the world itself: it gets the world's sound, not its decor."""
    if not set_id: return sc
    from .art import FULL_FRAME
    w = SETS[set_id](dur, random.Random(f'{set_id}|{seed}'))
    if template in FULL_FRAME or sc.get('full_frame'): w = {**w, 'elements': []}
    back = [e for e in w['elements'] if e.get('behind')]
    front = [e for e in w['elements'] if not e.get('behind')]       # edge and bottom decor (weeds, vials, skyline): over a full-frame map too
    sc['elements'] = back + sc['elements'] + front
    sc.setdefault('beds', []).extend({'name': n, 'gain': g} for n, g in w['beds'])
    sc.setdefault('sfx', []).extend({'at': round(a, 2), 'name': n, 'gain': g} for a, n, g in w['sfx'] if a < dur)
    sc['set'] = set_id
    return sc
