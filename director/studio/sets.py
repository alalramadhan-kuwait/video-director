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


def _motes(rng, n, color, dur, y0=150, y1=1150, rise=60, r=(1.5, 3.5), op=.35, depth=(.5, .9), behind=True, x0=20, x1=700):
    out = []
    for _ in range(n):
        rr = rng.uniform(*r); x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
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


# ------------------------------------------------------------------------------------------- shared pieces (rule 18g)
def _sky(*stops):                     # a backdrop with more than two colours: [(offset, colour), ...]
    i = uid('bd')
    s = ''.join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in stops)
    return _el(f'<defs><linearGradient id="{i}" x1="0" y1="0" x2="0" y2="1">{s}</linearGradient></defs><rect width="{W}" height="{H}" fill="url(#{i})"/>',
               behind=True, depth=0)


def _band(body, top, **kw):             # decor drawn on the full card but kept to its lower band (from y = top down), so
    h = H - top                          # the element's own box says where it is: below the middle
    return _el(f'<g transform="translate(0 {-top})">{body}</g>', W, h, 360, top - 20 + h / 2, **kw)


def _glow(color, size, op=.5):       # a soft round light (a lamp, a flash, a window at night)
    i = uid('glow')
    return (f'<defs><radialGradient id="{i}"><stop offset="0" stop-color="{color}" stop-opacity="{op}"/><stop offset="1" stop-color="{color}" '
            f'stop-opacity="0"/></radialGradient></defs><circle cx="{size / 2}" cy="{size / 2}" r="{size / 2}" fill="url(#{i})"/>')


def _breath(dur, lo, hi, period=2.4):  # an opacity that breathes slowly for the whole scene
    n = max(2, int(dur / period * 2) + 1)
    return [[round(k * dur / (n - 1), 2), hi if k % 2 else lo] for k in range(n)]


def _bust(x, y, s, color):           # a faceless person seen from behind: head, shoulders, a body that runs off below
    return (f'<ellipse cx="{x}" cy="{y}" rx="{15 * s:.1f}" ry="{18 * s:.1f}" fill="{color}"/>'
            f'<path d="M{x - 40 * s:.1f} {y + 200 * s:.1f} L{x - 40 * s:.1f} {y + 56 * s:.1f} Q{x - 38 * s:.1f} {y + 24 * s:.1f} {x} {y + 22 * s:.1f} '
            f'Q{x + 38 * s:.1f} {y + 24 * s:.1f} {x + 40 * s:.1f} {y + 56 * s:.1f} L{x + 40 * s:.1f} {y + 200 * s:.1f} Z" fill="{color}"/>')


def _chair(x, y, w, color, edge):    # the back of a sale-room chair, seen from the rows behind
    h = w * 1.5
    return (f'<rect x="{x - w / 2:.1f}" y="{y}" width="{w}" height="{h * .62:.1f}" rx="{w * .16:.1f}" fill="{color}"/>'
            f'<rect x="{x - w / 2 + 4:.1f}" y="{y + 3}" width="{w - 8}" height="4" rx="2" fill="{edge}"/>'
            f'<rect x="{x - w / 2 + 4:.1f}" y="{y}" width="{w * .12:.1f}" height="{h * 1.4:.1f}" fill="{color}"/>'
            f'<rect x="{x + w / 2 - 4 - w * .12:.1f}" y="{y}" width="{w * .12:.1f}" height="{h * 1.4:.1f}" fill="{color}"/>')


def _fir(x, base, h, fill, snow=None):   # a fir of four tiers, snow on each tier's top edge
    out = f'<rect x="{x - h * .03:.1f}" y="{base - h * .12:.1f}" width="{h * .06:.1f}" height="{h * .12:.1f}" fill="{fill}"/>'
    for i in range(4):
        w = h * (.36 - i * .07); b = base - h * .1 - i * h * .21; top = b - h * .34
        out += f'<path d="M{x - w:.1f} {b:.1f} L{x} {top:.1f} L{x + w:.1f} {b:.1f} Z" fill="{fill}"/>'
        if snow:
            out += (f'<path d="M{x} {top:.1f} L{x + w * .34:.1f} {top + h * .11:.1f} L{x + w * .12:.1f} {top + h * .09:.1f} L{x - w * .05:.1f} {top + h * .12:.1f} '
                    f'L{x - w * .3:.1f} {top + h * .1:.1f} Z" fill="{snow}" fill-opacity=".85"/>')
    return out


def _ridge(rng, y, amp, n, color):        # a mountain ridge across the width: a smooth line of n bumps around y
    pts = [(x, y + rng.uniform(-amp, amp)) for x in [-40 + k * (W + 80) / n for k in range(n + 1)]]
    d = f'M-40 {H} L{pts[0][0]:.0f} {pts[0][1]:.0f}'
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        d += f' Q{(x0 + x1) / 2:.0f} {min(y0, y1) - amp * .6:.0f} {x1:.0f} {y1:.0f}'
    return f'<path d="{d} L{W + 40} {H} Z" fill="{color}"/>', pts


def _rise(y0, lift, t, hold=1.3):         # a paddle (or a hand) that comes up at t, holds, and goes back down
    return [[0, y0], [t, y0], [t + .3, y0 - lift, 'outBack'], [t + .3 + hold, y0 - lift], [t + .75 + hold, y0]]


# ------------------------------------------------------------------------------------------------- the new worlds
def auction_room(dur, rng):
    """A dark panelled sale room: the lot's real photo sits in the empty frame on the wall, the auctioneer stands at the
    rostrum in a warm spot, and paddles go up in the rows as the bidding runs."""
    from . import drawn
    els = [_backdrop('#2C2521', '#0F0C0A')]
    panels = (f'<rect y="0" width="{W}" height="128" fill="#1A1512"/><rect y="128" width="{W}" height="12" fill="#4A3B2F"/>'
              + ''.join(f'<rect x="{18 + i * 124}" y="176" width="100" height="660" rx="3" fill="none" stroke="#4E3F33" stroke-opacity=".55" stroke-width="3"/>'
                        f'<rect x="{18 + i * 124}" y="880" width="100" height="120" rx="3" fill="none" stroke="#4E3F33" stroke-opacity=".55" stroke-width="3"/>'
                        for i in range(6))
              + f'<rect y="852" width="{W}" height="12" fill="#3A2E25"/>')
    els.append(_el(panels, behind=True, depth=.3))
    screen = ('<rect x="0" y="0" width="500" height="620" fill="#0B0908" fill-opacity=".72" stroke="#8C7A5A" stroke-opacity=".55" stroke-width="5"/>'
              '<rect x="14" y="14" width="472" height="592" fill="none" stroke="#8C7A5A" stroke-opacity=".25" stroke-width="2"/>')
    els.append({**_el(screen, 500, 620, 350, 570), 'behind': True, 'depth': .35})        # the empty frame: the scene's real photo sits here
    i = uid('wash')
    cone = (f'<defs><linearGradient id="{i}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#F3D9A4" stop-opacity=".22"/>'
            f'<stop offset="1" stop-color="#F3D9A4" stop-opacity=".04"/></linearGradient></defs>'
            f'<polygon points="640,0 700,0 {W},1000 540,1000" fill="url(#{i})"/>')
    els.append(_el(cone, behind=True, depth=.4, opacity=_breath(dur, .85, 1, 3.2)))
    els.append({**_el(_glow('#F3D9A4', 360, .32), 360, 360, 650, 800), 'behind': True, 'depth': .4})
    svg, w0, h0 = drawn.person('man_suit', uid=uid('dr'), hat=False)                   # the auctioneer: faceless, drawn
    fh = 380; fw = w0 * fh / h0
    svg = svg.replace(f'width="{w0}" height="{h0}"', f'width="{fw:.0f}" height="{fh}"', 1)
    els.append({'type': 'svg', 'svg': svg, 'w': round(fw), 'h': fh, 'x': 650, 'y': 940 - fh * .578 + fh / 2, 'anchor': 'c', 'still': True,
                'behind': True, 'depth': .4, 'idle': {'type': 'sway', 'amp': .6, 'speed': .25}})
    rostrum = ('<path d="M0 14 L150 14 L140 260 L10 260 Z" fill="#3A2A20"/><rect x="-6" y="0" width="162" height="16" rx="3" fill="#5A4232"/>'
               '<rect x="24" y="44" width="102" height="150" rx="4" fill="none" stroke="#5A4232" stroke-width="3"/>'
               '<rect x="96" y="-10" width="40" height="11" rx="4" fill="#5E4634"/><rect x="112" y="-4" width="8" height="5" fill="#5E4634"/>')
    els.append({**_el(f'<g transform="translate(8 12)">{rostrum}</g>', 170, 280, 650, 1070), 'behind': True, 'depth': .4})
    xs = [40 + i * 76 for i in range(10)]
    els.append(_el(''.join(_bust(x + 20, 1000, .85, '#1C1714') for x in xs if rng.random() > .2), behind=True, depth=.55))
    times = [1.0, 1.6, 2.2] + ([round(dur * .62, 2)] if dur > 5 else []) + ([round(dur * .8, 2)] if dur > 7.5 else [])
    seats = rng.sample(xs[:8], len(times))
    paddle = ('<rect x="19" y="34" width="6" height="64" fill="#8A6E52"/><rect x="0" y="0" width="44" height="38" rx="6" fill="#EFE8DA"/>'
              '<rect x="8" y="16" width="28" height="5" rx="2" fill="#2B2420" fill-opacity=".55"/>')
    for x, t in zip(seats, times):                                       # paddles go up one after another
        els.append({**_el(paddle, 44, 98, x - 20 + rng.uniform(-12, 12), _rise(1100, 92, t, hold=rng.uniform(1.0, 1.5))),
                    'behind': True, 'depth': .55, 'rot': rng.uniform(-8, 8)})
    els.append(_el(''.join(_chair(x + 20, 1040, 58, '#2E2420', '#4A3A2E') for x in xs), behind=True, depth=.55))
    near = (''.join(_bust(x, 1150, 1.35, '#120E0C') for x in range(30, W, 140))
            + ''.join(_chair(x, 1196, 96, '#1E1714', '#3A2E25') for x in range(-10, W + 60, 112)))
    els.append({**_band(near, 1120), 'depth': .85, 'crop': True, 'underCaptions': True})
    els += _motes(rng, 10, '#F3D9A4', dur, y0=300, y1=900, rise=30, op=.4, x0=560, x1=720)
    return {'theme': 'tk-ink', 'elements': els, 'beds': [('room', -30), ('crowd', -38)], 'sfx': []}


def paris_rail(dur, rng):
    """A railway line outside Paris at dusk: the city far off, catenary posts and the rails, and a train with lit
    windows that crosses during the scene."""
    from .cities import paris as _paris_sky
    els = [_sky((0, '#2C3240'), (.45, '#5E5A6C'), (.72, '#A9837C'), (1, '#D6A883'))]
    for _ in range(14):
        x, y, r = rng.uniform(20, 740), rng.uniform(30, 380), rng.uniform(.8, 1.8)
        els.append(_el(f'<circle cx="3" cy="3" r="{r}" fill="#F3F0E8"/>', 6, 6, x, y, behind=True, depth=.15, opacity=round(rng.uniform(.25, .6), 2)))
    els.append({**_el(_glow('#E7B98A', 700, .45), 700, 700, 470, 960), 'behind': True, 'depth': .2})        # the last light
    c = {'far': '#5F5B6B', 'mid': '#4B4859', 'near': '#3B3A49', 'line': '#F1D49A', 'water': '#5F5B6B', 'accent': '#3B3A49'}
    for body, depth in zip(_paris_sky(c), (.3, .4, .5)):
        els.append({**_el(body, 720, 440, 330, 790, depth=depth, behind=True), 'scale': 1.12})
    ground = (f'<rect y="1010" width="{W}" height="{H - 1010}" fill="#25252D"/><rect y="1010" width="{W}" height="6" fill="#3A3946"/>'
              f'<rect y="1056" width="{W}" height="3" fill="#8A8494"/><rect y="1068" width="{W}" height="3" fill="#8A8494"/>'
              + ''.join(f'<path d="M{x} 1058 L{x + (x - 380) * .05:.0f} 1074" stroke="#3E3D4A" stroke-width="4"/>' for x in range(-20, W + 20, 22))
              + f'<rect y="1180" width="{W}" height="70" fill="#2E2D37"/>'
              + ''.join(f'<path d="M{x} 1196 L{x + (x - 380) * .14:.0f} 1246" stroke="#45434F" stroke-width="10"/>' for x in range(-40, W + 60, 40))
              + f'<rect y="1196" width="{W}" height="7" fill="#A29CAC"/><rect y="1236" width="{W}" height="8" fill="#A29CAC"/>')
    posts = ''.join(f'<rect x="{x}" y="986" width="4" height="74" fill="#3E3D4A"/><rect x="{x - 14}" y="992" width="22" height="3" fill="#3E3D4A"/>'
                    for x in range(30, W, 150))
    posts += ''.join(f'<path d="M{x - 10} 994 Q {x + 65} 1004 {x + 140} 994" stroke="#3E3D4A" stroke-width="1.4" fill="none"/>' for x in range(30, W, 150))
    els.append(_el(ground + posts, behind=True, depth=.8))
    t0 = round(min(.6, dur * .1), 2); t1 = round(max(t0 + 3.2, dur * .9), 2)
    cars = ('<rect x="10" y="78" width="220" height="62" rx="10" fill="#3F4A5A"/><path d="M10 120 L0 120 L14 84 Q 20 78 40 78 L40 120 Z" fill="#3F4A5A"/>'
            '<rect x="18" y="88" width="24" height="18" rx="3" fill="#F1D49A" fill-opacity=".9"/><rect x="10" y="126" width="220" height="6" fill="#B07C5E"/>'
            '<path d="M110 78 L130 30 L150 78 M120 54 L140 54" stroke="#1E2228" stroke-width="3" fill="none"/>'
            '<rect x="112" y="26" width="38" height="5" fill="#1E2228"/>'
            + ''.join(f'<rect x="{x}" y="90" width="22" height="16" rx="3" fill="#F1D49A" fill-opacity=".8"/>' for x in (64, 94, 170, 200))
            + ''.join(f'<rect x="{240 + k * 250}" y="80" width="240" height="60" rx="8" fill="#4E5A4E"/>'
                      f'<rect x="{240 + k * 250}" y="80" width="240" height="8" rx="4" fill="#3E4A3E"/>'
                      + ''.join(f'<rect x="{254 + k * 250 + j * 38}" y="96" width="28" height="20" rx="3" fill="#F1D49A" '
                                f'fill-opacity="{.55 + .35 * ((j + k) % 3 == 0):.2f}"/>' for j in range(6))
                      for k in range(3))
            + ''.join(f'<circle cx="{x}" cy="142" r="9" fill="#14161A"/>' for x in [40, 70, 180, 210] + [260 + k * 250 + d for k in range(3) for d in (10, 40, 180, 210)]))
    tw, th = 1000, 152
    xa, xb = 360 + 360 + tw / 2 + 40, 360 - 360 - tw / 2 - 40
    els.append({**_el(cars, tw, th, [[0, xa], [t0, xa], [t1, xb, 'linear']], 1112), 'depth': 1.0, 'crop': True, 'underCaptions': True,
                'idle': {'type': 'bob', 'amp': 1.2, 'speed': 3}})
    k = 0
    while k < 16:                                                        # vapour from under the train, drifting up and away
        tb = t0 + .2 + k * (t1 - t0) / 16
        if tb > dur - .4: break
        x = xa + (xb - xa) * (tb - t0) / (t1 - t0) - tw / 2 + rng.uniform(40, 600); r = rng.uniform(26, 40)
        els.append(_el(_glow('#E9E2CF', 2 * r, .5), 2 * r, 2 * r, [[0, x], [tb, x], [tb + 2.2, x + 90]],
                       [[0, 1150], [tb, 1150], [tb + 2.2, 1010]], behind=False, depth=1.0, underCaptions=True, crop=True,
                       opacity=[[0, 0], [tb, 0], [tb + .3, .8], [tb + 2.2, 0]]))
        k += 1
    near = (''.join(f'<rect x="{x}" y="1050" width="14" height="300" fill="#1A1A20"/><rect x="{x - 6}" y="1044" width="26" height="10" fill="#1A1A20"/>'
                    f'<rect x="{min(x, x + d * 80)}" y="1060" width="80" height="5" fill="#1A1A20"/>' for x, d in ((20, 1), (726, -1)))
            + f'<path d="M20 1066 Q 380 1080 740 1066" stroke="#1A1A20" stroke-width="2" fill="none"/>'
            f'<path d="M20 1082 L740 1082" stroke="#1A1A20" stroke-width="1.6" fill="none"/>')
    els.append({**_band(near, 1040), 'depth': 1.1, 'crop': True, 'underCaptions': True})
    els += _motes(rng, 12, '#E9E2CF', dur, y0=860, y1=1100, rise=60, op=.3)
    return {'theme': 'tk-graphite', 'elements': els, 'beds': [('train', -24)], 'sfx': []}


def _kitchen(dur, rng):
    els = [_backdrop('#E4D5B5', '#CDB792')]
    paper = ''.join(f'<circle cx="{x + (40 if (y // 90) % 2 else 0)}" cy="{y}" r="20" fill="none" stroke="#9C6B3E" stroke-width="5"/>'
                    f'<circle cx="{x + (40 if (y // 90) % 2 else 0)}" cy="{y}" r="7" fill="#9C6B3E"/>' for x in range(0, W + 80, 80) for y in range(60, 1100, 90))
    els.append(_el(paper, behind=True, depth=.3, opacity=.09))
    i = uid('wash')
    window = (f'<defs><linearGradient id="{i}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#55617A"/><stop offset=".7" stop-color="#C79A80"/>'
              f'<stop offset="1" stop-color="#E7B98A"/></linearGradient></defs><rect x="14" y="14" width="232" height="372" fill="url(#{i})"/>'
              '<path d="M14 386 L14 300 L60 300 L60 270 L104 270 L104 290 L150 290 L150 250 L196 250 L196 296 L246 296 L246 386 Z" fill="#4A4552"/>'
              '<rect x="120" y="300" width="9" height="12" fill="#F1D49A"/><rect x="72" y="284" width="8" height="10" fill="#F1D49A" fill-opacity=".7"/>'
              '<rect x="0" y="0" width="260" height="400" fill="none" stroke="#EFE7D6" stroke-width="28"/>'
              '<rect x="124" y="0" width="12" height="400" fill="#EFE7D6"/><rect x="0" y="194" width="260" height="12" fill="#EFE7D6"/>'
              '<rect x="-14" y="396" width="288" height="18" fill="#D9CCB2"/>')
    els.append({**_el(window, 260, 416, 150, 360), 'behind': True, 'depth': .4})
    for x, ph in ((44, 0), (256, 1.5)):
        curtain = '<path d="M0 0 L70 0 L64 170 Q 34 182 6 170 Z" fill="#C58B54" fill-opacity=".85"/>' + ''.join(
            f'<path d="M{12 + j * 16} 6 L{10 + j * 15} 168" stroke="#A9733F" stroke-width="2"/>' for j in range(4))
        els.append({**_el(curtain, 70, 182, x, 242), 'behind': True, 'depth': .4, 'idle': {'type': 'sway', 'amp': .8, 'speed': .2, 'phase': ph}})
    light = '<polygon points="0,0 220,0 420,560 120,560" fill="#F3D9A4" fill-opacity=".14"/>'
    els.append({**_el(light, 420, 560, 330, 840), 'behind': True, 'depth': .5, 'opacity': _breath(dur, .7, 1, 4)})
    cupboards = ('<rect x="0" y="0" width="210" height="250" fill="#A8865E"/><rect x="0" y="246" width="210" height="10" fill="#8C6E4E"/>'
                 + ''.join(f'<rect x="{8 + k * 100}" y="10" width="92" height="226" rx="4" fill="none" stroke="#8C6E4E" stroke-width="4"/>'
                           f'<rect x="{k * 100 + (82 if k == 0 else 18)}" y="190" width="6" height="26" rx="3" fill="#E9DFC9"/>' for k in range(2)))
    counter = ('<rect x="0" y="0" width="230" height="22" fill="#D8CDB6"/><rect x="0" y="22" width="230" height="460" fill="#A8865E"/>'
               + ''.join(f'<rect x="{10 + k * 110}" y="40" width="100" height="200" rx="4" fill="none" stroke="#8C6E4E" stroke-width="4"/>'
                         f'<rect x="{50 + k * 110}" y="60" width="22" height="6" rx="3" fill="#E9DFC9"/>' for k in range(2))
               + '<path d="M40 0 L44 -50 Q 60 -64 76 -50 L80 0 Z" fill="#B5483C" fill-opacity=".8"/><rect x="54" y="-62" width="12" height="8" fill="#5A3A30"/>'
               '<rect x="110" y="-44" width="34" height="44" rx="5" fill="#E9DFC9"/><rect x="110" y="-50" width="34" height="8" rx="3" fill="#8C6E4E"/>')
    els.append({**_el(cupboards, 210, 256, 655, 300), 'behind': True, 'depth': .45})
    els.append({**_el(f'<g transform="translate(0 70)">{counter}</g>', 230, 560, 645, 1070), 'behind': True, 'depth': .55})
    floor = (f'<rect y="1080" width="{W}" height="{H - 1080}" fill="#A69476"/>'
             + ''.join(f'<rect x="{x + (30 if (y // 30) % 2 else 0)}" y="{y}" width="30" height="30" fill="#B9A88A"/>'
                       for x in range(0, W + 60, 60) for y in range(1080, H, 30)))
    els.append(_el(floor, behind=True, depth=.6))
    els.append({**_el(_glow('#FFD27A', 600, .95), 600, 600, 470, 230), 'behind': True, 'depth': .35, 'opacity': _breath(dur, .55, 1, 2.6)})
    lamp = ('<rect x="58" y="0" width="4" height="150" fill="#3A2E25"/><path d="M10 206 Q 14 150 60 146 Q 106 150 110 206 Z" fill="#B5733F"/>'
            '<rect x="6" y="200" width="108" height="8" rx="4" fill="#8C5530"/><ellipse cx="60" cy="210" rx="30" ry="6" fill="#FBE6B8"/>')
    els.append({**_el(lamp, 120, 220, 470, 100), 'behind': True, 'depth': .35, 'idle': {'type': 'sway', 'amp': .5, 'speed': .2}})
    cloth = ''.join(f'<rect x="{x}" y="{y}" width="26" height="26" fill="#B5734A" fill-opacity="{.85 if ((x // 26) + (y // 26)) % 2 else .35}"/>'
                    for x in range(0, 560, 26) for y in range(0, 156, 26))
    i = uid('wash')
    table = (f'<defs><clipPath id="{i}"><path d="M20 0 L540 0 L560 150 L0 150 Z"/></clipPath></defs><path d="M20 0 L540 0 L560 150 L0 150 Z" fill="#EDE2CB"/>'
             f'<g clip-path="url(#{i})">{cloth}</g><rect x="40" y="150" width="20" height="200" fill="#6E5440"/><rect x="500" y="150" width="20" height="200" fill="#6E5440"/>'
             '<ellipse cx="130" cy="20" rx="46" ry="12" fill="#E9DFC9"/><path d="M84 18 Q 130 52 176 18 Z" fill="#D8CDB6"/>')
    els.append({**_el(table, 560, 350, 350, 1180), 'depth': .9, 'crop': True, 'underCaptions': True})
    return els


def home_70s(dur, rng):
    """A modest 1970s kitchen in the evening: a window on the last light, a table, a lamp whose glow breathes."""
    return {'theme': 'tk-linen', 'elements': _kitchen(dur, rng), 'beds': [('room', -30)], 'sfx': []}


def home_70s_driver(dur, rng):
    """The same kitchen, and the father, a train driver drawn faceless in paper (drawn.rail_driver), walks in from the
    right and stops at the side, leaving the middle to the scene's own picture."""
    from . import drawn
    els = _kitchen(dur, rng)
    at = round(min(.6, dur * .1), 2)
    walker = drawn.walk_in('rail_driver', uid=uid('dr'), at=at, walk=min(2.4, max(1.2, dur * .4)), from_x=880, to_x=622, bottom=1090, h=500, depth=.6)
    els.insert(len(els) - 1, walker)                                     # behind the table, in front of the counter
    return {'theme': 'tk-linen', 'elements': els, 'beds': [('room', -30)], 'sfx': [(at + .1, 'footsteps', -20)]}


def paris_atelier(dur, rng):
    """A restorer's bench by a window over the zinc roofs of Paris: tool shelves, a lamp, dust in its light. Gears and
    tools only: no watch and no dial is ever drawn (the real ones are shown in their photos)."""
    els = [_backdrop('#DDD4C2', '#B5A890')]
    i = uid('wash')
    roofs = ''.join(f'<path d="M{x} 600 L{x} {y + 30} L{x + 16} {y} L{x + w - 16} {y} L{x + w} {y + 30} L{x + w} 600 Z" fill="{col}"/>'
                    + ''.join(f'<rect x="{x + 18 + j * 34}" y="{y + 6}" width="16" height="20" rx="7" fill="#5E676E" stroke="#DDE1E2" stroke-width="2.5"/>' for j in range((w - 30) // 34))
                    + f'<rect x="{x + w * .3:.0f}" y="{y - 26}" width="22" height="28" fill="#A98468"/>'
                    + ''.join(f'<rect x="{x + w * .3 + 3 + j * 6:.0f}" y="{y - 36}" width="4" height="12" fill="#B5866A"/>' for j in range(3))
                    for x, y, w, col in ((-10, 330, 170, '#9AA3AA'), (150, 300, 150, '#8E979E'), (290, 350, 140, '#9AA3AA'), (0, 420, 220, '#7C868E'),
                                         (210, 410, 230, '#848E96')))
    window = (f'<defs><linearGradient id="{i}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#E2E6E6"/><stop offset="1" stop-color="#C9D1D3"/>'
              f'</linearGradient></defs><rect width="420" height="600" fill="url(#{i})"/>{roofs}'
              '<rect width="420" height="600" fill="none" stroke="#EFE9DC" stroke-width="24"/>'
              + ''.join(f'<rect x="{x}" y="0" width="7" height="600" fill="#EFE9DC"/>' for x in (138, 275))
              + ''.join(f'<rect x="0" y="{y}" width="420" height="7" fill="#EFE9DC"/>' for y in (196, 396))
              + '<rect x="-16" y="596" width="452" height="20" fill="#D2C6AE"/>')
    els.append({**_el(window, 420, 616, 230, 420), 'behind': True, 'depth': .35})
    shaft = '<polygon points="0,0 200,0 520,700 260,700" fill="#FFFFFF" fill-opacity=".16"/>'
    els.append({**_el(shaft, 520, 700, 420, 820), 'behind': True, 'depth': .45, 'opacity': _breath(dur, .6, 1, 5)})
    shelf = ''
    for k, y in enumerate((60, 260, 460)):
        shelf += f'<rect x="0" y="{y + 120}" width="180" height="12" fill="#7A5E44"/>'
        if k == 0:
            shelf += ''.join(f'<rect x="{10 + j * 40}" y="{y + 50}" width="30" height="70" rx="4" fill="#C9D1D3" fill-opacity=".6" stroke="#8E979E" stroke-width="2"/>'
                             f'<rect x="{8 + j * 40}" y="{y + 42}" width="34" height="10" rx="2" fill="#7A5E44"/>' for j in range(4))
        elif k == 1:
            shelf += ''.join(f'<rect x="{6 + c * 42}" y="{y + 30 + r * 30}" width="38" height="26" fill="#9C7A58" stroke="#6E5440" stroke-width="2"/>'
                             f'<circle cx="{25 + c * 42}" cy="{y + 43 + r * 30}" r="3" fill="#E9DFC9"/>' for c in range(4) for r in range(3))
        else:
            shelf += ('<rect x="10" y="{0}" width="60" height="50" fill="#8C7A5A"/><rect x="80" y="{1}" width="40" height="70" fill="#6E5440"/>'
                      '<circle cx="150" cy="{2}" r="22" fill="none" stroke="#6E675C" stroke-width="5"/>').format(y + 70, y + 50, y + 98)
    els.append({**_el(shelf, 180, 600, 640, 560), 'behind': True, 'depth': .6})
    rack = '<rect x="0" y="0" width="90" height="10" fill="#7A5E44"/>' + ''.join(
        f'<rect x="{10 + j * 16}" y="10" width="4" height="{60 + (j % 3) * 14}" fill="#6E675C"/><rect x="{8 + j * 16}" y="10" width="8" height="18" rx="2" fill="#{c}"/>'
        for j, c in enumerate(('8E5A3A', '4C5660', '8C7A5A', '5E6B5A', '8E5A3A')))
    els.append({**_el(rack, 90, 110, 60, 700), 'behind': True, 'depth': .6})
    i = uid('wash')
    cone = (f'<defs><linearGradient id="{i}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#F6D9A0" stop-opacity=".4"/>'
            f'<stop offset="1" stop-color="#F6D9A0" stop-opacity=".1"/></linearGradient></defs><polygon points="150,10 210,0 380,210 60,210" fill="url(#{i})"/>')
    els.append({**_el(cone, 380, 210, 230, 875), 'behind': True, 'depth': .95, 'opacity': _breath(dur, .8, 1, 3)})
    lamp = ('<rect x="10" y="230" width="60" height="10" rx="4" fill="#3A3D44"/><path d="M40 232 L70 90 L150 40" stroke="#3A3D44" stroke-width="8" fill="none" stroke-linecap="round"/>'
            '<circle cx="70" cy="90" r="7" fill="#2A2D33"/><path d="M128 20 L190 44 L172 82 L110 58 Z" fill="#4C5660"/>')
    els.append({**_el(lamp, 200, 240, 110, 860), 'behind': True, 'depth': .95})
    els += _motes(rng, 16, '#FFF4D6', dur, y0=800, y1=960, rise=24, op=.55, r=(1, 2.4), x0=150, x1=380, depth=(.9, 1))
    gear = _gear(22, 12, '#8C7A5A') + f'<g transform="translate(40 14)">{_gear(14, 10, "#A9947A")}</g>'
    bench = (f'<rect y="0" width="{W}" height="22" fill="#8A6A4C"/><rect y="22" width="{W}" height="10" fill="#6E5440"/><rect x="90" y="-4" width="580" height="8" rx="3" fill="#9FB0A0"/>'
             f'<rect y="32" width="{W}" height="300" fill="#7A5E44"/>'
             + ''.join(f'<rect x="{20 + k * 150}" y="54" width="130" height="80" rx="4" fill="none" stroke="#5E4634" stroke-width="4"/>'
                       f'<rect x="{70 + k * 150}" y="90" width="30" height="8" rx="4" fill="#C9BFA8"/>' for k in range(5))
             + f'<g transform="translate(470 -34)"><rect x="0" y="22" width="110" height="12" rx="4" fill="#C9C3B4"/>{gear}</g>'
             '<path d="M180 -6 L292 -16 M180 -2 L292 -14" stroke="#6E675C" stroke-width="3" stroke-linecap="round"/>'
             '<rect x="330" y="-26" width="34" height="24" rx="6" fill="#2A2D33"/><rect x="336" y="-30" width="22" height="6" fill="#4C5660"/>'
             + ''.join(f'<rect x="{620 + j * 12}" y="-60" width="5" height="58" fill="#6E675C"/><rect x="{619 + j * 12}" y="-66" width="7" height="12" rx="2" fill="#{c}"/>'
                       for j, c in enumerate(('8E5A3A', '4C5660', '8C7A5A', '5E6B5A')))
             + '<rect x="610" y="-6" width="60" height="8" rx="3" fill="#5E4634"/>')
    els.append({**_el(f'<g transform="translate(0 70)">{bench}</g>', W, 400, 360, 1110), 'depth': 1.05, 'crop': True, 'underCaptions': True})
    return {'theme': 'tk-bone', 'elements': els, 'beds': [('watch_run', -26), ('crowd', -40)], 'sfx': []}


def jura(dur, rng):
    """The Jura in winter at dusk: ridges in layers, firs, snow falling, fog drifting and the village lights coming on."""
    els = [_sky((0, '#363F4C'), (.6, '#7A8690'), (1, '#A3ABAE'))]
    layers = (('#8E99A3', 640, 40, 5, .2), ('#6E7A86', 770, 36, 6, .3), ('#505C67', 900, 26, 7, .45), ('#353E47', 1030, 22, 8, .65))
    for k, (col, y, amp, n, depth) in enumerate(layers):
        body, pts = _ridge(rng, y, amp, n, col)
        if k == 0:                                                       # snow on the far tops
            for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                top = (y0 + y1) / 4 + (min(y0, y1) - amp * .6) / 2; xm = (x0 + x1) / 2
                body += f'<path d="M{xm - 46:.0f} {top + 12:.0f} Q{xm:.0f} {top - 3:.0f} {xm + 46:.0f} {top + 12:.0f} Q{xm:.0f} {top + 6:.0f} {xm - 46:.0f} {top + 12:.0f} Z" fill="#DDE2E5" fill-opacity=".75"/>'
        if k == 2:                                                       # the village on the slope: houses and a church tower
            body += ''.join(f'<rect x="{x}" y="{y - 18 + dy}" width="22" height="20" fill="#3E4954"/><path d="M{x - 3} {y - 18 + dy} L{x + 11} {y - 30 + dy} '
                            f'L{x + 25} {y - 18 + dy} Z" fill="#3E4954"/>' for x, dy in ((250, 8), (280, 2), (318, 6), (420, 4), (452, 10), (488, 6)))
            body += f'<rect x="364" y="{y - 70}" width="18" height="74" fill="#3E4954"/><path d="M360 {y - 70} L373 {y - 108} L386 {y - 70} Z" fill="#3E4954"/>'
        if k == 3:
            body += ''.join(_fir(x, yy + 28, rng.uniform(70, 110), '#2A323A') for x, yy in pts[::2])
        els.append(_el(body, behind=True, depth=depth))
        if k == 1:
            for j, (fy, d) in enumerate(((820, .35), (930, .5))):
                i = uid('wash')
                fog = (f'<defs><filter id="{i}" x="-20%" y="-50%" width="140%" height="200%"><feGaussianBlur stdDeviation="18"/></filter></defs>'
                       f'<ellipse cx="300" cy="60" rx="280" ry="34" fill="#D9DEE2" fill-opacity=".35" filter="url(#{i})"/>')
                x0 = rng.uniform(160, 560)
                els.append({**_el(fog, 600, 120, [[0, x0], [dur, x0 + (60 if j % 2 else -60)]], fy), 'behind': True, 'depth': d})
    spots = [(x + 11, 900 + dy - 9) for x, dy in ((250, 8), (280, 2), (318, 6), (420, 4), (452, 10), (488, 6))] + [(373, 846)]
    spots += [(rng.uniform(200, 560), rng.uniform(905, 940)) for _ in range(5)]
    for j, (x, y) in enumerate(spots):                                   # the village lights come on one by one
        on = round(rng.uniform(.5, max(1.0, dur * .7)), 2)
        els.append({**_el(_glow('#F6D9A0', 26, 1) + '<rect x="11" y="10" width="4" height="5" fill="#F6D9A0"/>', 26, 26, x - 20, y - 20), 'behind': True, 'depth': .45,
                    'opacity': [[0, 0], [on, 0], [on + .5, round(rng.uniform(.7, 1), 2)]]})
    i = uid('wash')
    fog = (f'<defs><filter id="{i}" x="-20%" y="-50%" width="140%" height="200%"><feGaussianBlur stdDeviation="22"/></filter></defs>'
           f'<ellipse cx="400" cy="70" rx="380" ry="40" fill="#D9DEE2" fill-opacity=".3" filter="url(#{i})"/>')
    els.append({**_el(fog, 800, 140, [[0, 420], [dur, 300]], 1010), 'behind': True, 'depth': .7})
    for j in range(46):                                                  # snow: each flake falls the whole height
        r = rng.uniform(1.5, 4.2); span = rng.uniform(6, 10); s = rng.uniform(-span, dur)
        x = rng.uniform(10, 710); y0 = -20 + max(0, -s) * 1360 / span
        flake = f'<circle cx="{r + 1:.1f}" cy="{r + 1:.1f}" r="{r:.1f}" fill="#F1F2F0"/>'
        els.append(_el(flake, 2 * r + 2, 2 * r + 2, x, [[max(0, s), y0], [s + span, 1340, 'linear']], behind=True, depth=round(.5 + r / 6, 2),
                       opacity=round(rng.uniform(.45, .9), 2), idle={'type': 'float', 'amp': rng.uniform(6, 14), 'speed': rng.uniform(.2, .4), 'phase': j}))
    for x, h, col in ((130, 330, '#232B32'), (40, 410, '#1E252B'), (630, 300, '#232B32'), (720, 420, '#1E252B')):    # near firs at the edges
        els.append({**_band(_fir(x, 1340, h, col, '#E4E8EA'), round(1340 - 1.08 * h)), 'depth': 1.15, 'crop': True, 'underCaptions': True})
    return {'theme': 'tk-graphite', 'elements': els, 'beds': [('wind', -24), ('bell_far', -34)], 'sfx': []}


def basel_fair(dur, rng):
    """A watch fair hall in 1998: roof trusses, blank hanging banners (no names, no logos), a lit empty vitrine at the
    centre-bottom where the scene's real photo belongs, a crowd moving slowly at three depths and camera flashes."""
    els = [_backdrop('#3C3E44', '#1B1C1F')]
    truss = ''
    for y, h, step in ((40, 54, 60), (190, 30, 40)):
        truss += f'<rect y="{y}" width="{W}" height="5" fill="#5A5C62"/><rect y="{y + h}" width="{W}" height="5" fill="#5A5C62"/>'
        truss += ''.join(f'<path d="M{x} {y + h} L{x + step / 2} {y + 4} L{x + step} {y + h}" stroke="#5A5C62" stroke-width="3" fill="none"/>' for x in range(-step, W + step, step))
    truss += ''.join(f'<path d="M{x - 14} 120 L{x + 14} 120 L{x + 22} 136 L{x - 22} 136 Z" fill="#2A2B2F"/><ellipse cx="{x}" cy="137" rx="16" ry="4" fill="#F3E6C4"/>'
                     for x in range(110, W, 180))
    els.append(_el(truss, behind=True, depth=.25))
    for x in range(110, W, 180):
        els.append({**_el(_glow('#F3E6C4', 220, .25), 220, 220, x - 20, 120), 'behind': True, 'depth': .25})
    booths = ''.join(f'<rect x="{x}" y="820" width="{w}" height="200" fill="#2F3136"/><rect x="{x}" y="800" width="{w}" height="22" fill="{c}"/>'
                     f'<rect x="{x + 10}" y="850" width="{w - 20}" height="60" fill="#F3E6C4" fill-opacity=".08"/>'
                     for x, w, c in ((-20, 200, '#5A5C62'), (200, 160, '#6E6458'), (380, 170, '#5A5C62'), (570, 210, '#6E6458')))
    els.append(_el(booths, behind=True, depth=.35))
    for x, w, h, col, ph in ((50, 70, 330, '#6E4A42', 0), (148, 58, 250, '#4C5660', 1), (612, 58, 270, '#8C7A5A', 2), (710, 70, 340, '#5E6B5A', 3)):
        banner = (f'<rect x="0" y="0" width="{w + 12}" height="8" rx="3" fill="#2A2B2F"/><rect x="6" y="8" width="{w}" height="{h}" fill="{col}"/>'
                  f'<path d="M6 {h + 8} L{6 + w / 2} {h - 14} L{6 + w} {h + 8} Z" fill="#2B2D32"/>'
                  f'<rect x="{6 + w * .15:.0f}" y="40" width="{w * .7:.0f}" height="3" fill="#F3F0E8" fill-opacity=".25"/>')
        els.append({**_el(banner, w + 12, h + 10, x - 20, 112 + h / 2), 'behind': True, 'depth': .3,
                    'idle': {'type': 'sway', 'amp': .7, 'speed': .18, 'phase': ph}})

    def crowd(n, y, s, col, depth, lo, hi, behind, skip=None):
        for j in range(n):
            x = lo + (hi - lo) * (j + rng.uniform(.1, .9)) / n
            if skip and skip[0] < x < skip[1]: continue
            dx = rng.choice((-1, 1)) * rng.uniform(20, 70) * depth
            yy = y + rng.uniform(-8, 8) * s
            el = {**_el(_bust(50 * s, 20 * s, s, col), 100 * s, 220 * s, [[0, x], [dur, x + dx, 'linear']], yy + 90 * s), 'depth': depth,
                  'behind': behind, 'idle': {'type': 'bob', 'amp': 2 * s, 'speed': rng.uniform(.3, .6), 'phase': j}}
            if not behind: el.update(crop=True, underCaptions=True)
            els.append(el)
    crowd(12, 900, .6, '#4A4C53', .45, -20, 740, True)
    i = uid('glow')
    vitrine = (f'<defs><radialGradient id="{i}" cx=".5" cy=".9" r=".7"><stop offset="0" stop-color="#FBF1D6" stop-opacity=".55"/>'
               f'<stop offset="1" stop-color="#FBF1D6" stop-opacity="0"/></radialGradient></defs>'
               '<rect x="20" y="170" width="200" height="300" fill="#2A2B30"/><rect x="14" y="160" width="212" height="14" fill="#55575E"/>'
               f'<rect x="30" y="10" width="180" height="150" fill="url(#{i})"/>'
               '<rect x="30" y="10" width="180" height="150" fill="#CFE0E6" fill-opacity=".1" stroke="#E4F0F3" stroke-opacity=".6" stroke-width="3"/>'
               '<path d="M50 24 L82 24 L42 140 L36 140 Z M94 24 L104 24 L70 140 L62 140 Z" fill="#FFFFFF" fill-opacity=".14"/>'
               '<rect x="26" y="4" width="188" height="8" fill="#55575E"/>')
    els.append({**_el(_glow('#FBF1D6', 420, .22), 420, 420, 360, 930), 'behind': True, 'depth': .6})
    els.append({**_el(vitrine, 240, 470, 360, 1080), 'behind': True, 'depth': .6})
    crowd(7, 1000, .95, '#2C2E33', .75, -20, 740, True, skip=(230, 490))
    times = sorted(round(rng.uniform(.8, max(1.2, dur - .6)), 2) for _ in range(3 if dur > 4 else 2))
    for t in times:                                                      # camera flashes in the crowd
        x, y = rng.choice((rng.uniform(40, 220), rng.uniform(500, 680))), rng.uniform(900, 1040)
        els.append({**_el(_glow('#FFFFFF', 180, .95), 180, 180, x, y), 'behind': True, 'depth': .75,
                    'opacity': [[0, 0], [max(0, t - .02), 0], [t, 1], [t + .1, .5], [t + .32, 0]]})
    crowd(2, 1120, 1.7, '#141518', 1.1, -40, 160, False)
    crowd(2, 1130, 1.7, '#141518', 1.1, 560, 760, False)
    return {'theme': 'tk-graphite', 'elements': els, 'beds': [('crowd', -28)], 'sfx': [(t, 'shutter', -24) for t in times[:2]]}


SETS = {'underwater': underwater, 'sea_night': sea_night, 'florence': florence, 'workshop': workshop, 'radium': radium, 'archive': archive,
        'auction_room': auction_room, 'paris_rail': paris_rail, 'home_70s': home_70s, 'home_70s_driver': home_70s_driver,
        'paris_atelier': paris_atelier, 'jura': jura, 'basel_fair': basel_fair}
NAME_AR = {'underwater': 'تحت الماء', 'sea_night': 'بحر ليلي وسفينة', 'florence': 'فلورنسا', 'workshop': 'ورشة الساعاتي',
           'radium': 'مختبر الراديوم', 'archive': 'مكتب الأرشيف', 'auction_room': 'قاعة المزاد', 'paris_rail': 'سكة حديد باريس عند الغروب',
           'home_70s': 'مطبخ من السبعينيات', 'home_70s_driver': 'مطبخ من السبعينيات وسائق القطار', 'paris_atelier': 'ورشة ترميم في باريس',
           'jura': 'جبال الجورا', 'basel_fair': 'معرض بازل 1998'}

# A sound a world asks for that the local kit (make-sfx.py) does not make yet plays its stand-in, or nothing, so a world
# never stops a render (render.mjs refuses an unknown sound). New sounds take over by themselves once the kit makes them.
STAND_IN = {'train': 'wind', 'gavel': None, 'footsteps': None}
_KIT: list[str] = []


def sound(name: str) -> str | None:
    """The sound to play for `name`: itself when the kit makes it, else its stand-in (None: leave it out)."""
    if not _KIT:
        from pathlib import Path
        f = Path(__file__).resolve().parents[2] / 'vendor/paper-story/scripts/make-sfx.py'
        _KIT.append(f.read_text(encoding='utf-8') if f.is_file() else '')
    return name if f"save('{name}'" in _KIT[0] else STAND_IN.get(name)


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
    beds, have = [], set()                                          # a stand-in never doubles a bed
    for n, g in w['beds']:
        n = sound(n)
        if n and n not in have: beds.append({'name': n, 'gain': g}); have.add(n)
    sc.setdefault('beds', []).extend(beds)
    sc.setdefault('sfx', []).extend({'at': round(a, 2), 'name': sound(n), 'gain': g} for a, n, g in w['sfx'] if a < dur and sound(n))
    sc['set'] = set_id
    return sc
