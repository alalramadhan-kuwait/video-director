"""A movement drawn the way a real one looks from the back (the owner: «رسمت المحركه سية جذا شوف محرك حقيقي»):
rose-gilt plate and bridges with Geneva stripes, gold wheels with spokes and teeth, a steel ratchet wheel with its
sunburst, a balance wheel with its blued hairspring under its cock, blued screws, rubies set in gold chatons.
A classic hand-wound layout, no brand, no calibre: a drawing of the principle (the screen says so)."""
from __future__ import annotations
import itertools, math, re

_uid = itertools.count(1)


def _unique(svg: str) -> str:
    """Every drawing gets its own ids: all scenes share one page, and a gradient defined in a hidden scene does not
    paint (the single movements came out dark)."""
    n = next(_uid)
    ids = set(re.findall(r'id="([A-Za-z]+)"', svg))
    for i in ids:
        svg = svg.replace(f'id="{i}"', f'id="{i}{n}"').replace(f'url(#{i})', f'url(#{i}{n})')
    return svg

PLATE = ('#D9A27F', '#A8694A')        # rose gilt, light to dark
GOLD = ('#F2D58A', '#B4893A')
STEEL = ('#EEF0F2', '#8E949B')
BLUE = '#2F4F9C'

# where the jewels sit that the back shows (centre, third, fourth, escape, pallet, balance), and four more for a 21
VISIBLE = [(300, 300), (392, 232), (440, 372), (378, 452), (292, 474), (176, 418)]
EXTRA = [(206, 206), (300, 122), (470, 250), (240, 330)]


def _teeth(cx, cy, r, n, depth):
    pts = []
    for i in range(n * 2):
        a = math.pi * i / n
        rr = r if i % 2 == 0 else r - depth
        pts.append(f'{cx + rr * math.cos(a):.1f},{cy + rr * math.sin(a):.1f}')
    return 'M' + ' L'.join(pts) + ' Z'


def _wheel(cx, cy, r, teeth, spokes=4):
    s = [f'<path d="{_teeth(cx, cy, r, teeth, r * .06)}" fill="url(#gold)" stroke="#7A5A22" stroke-width="1"/>',
         f'<circle cx="{cx}" cy="{cy}" r="{r * .8:.1f}" fill="url(#plate)" stroke="#7A5A22" stroke-width="1"/>']
    for k in range(spokes):                     # cut-outs between the spokes show the plate below
        a0 = 2 * math.pi * k / spokes + .25; a1 = a0 + 2 * math.pi / spokes - .5
        r0, r1 = r * .22, r * .74
        p = (f'M{cx + r0 * math.cos(a0):.1f} {cy + r0 * math.sin(a0):.1f} L{cx + r1 * math.cos(a0):.1f} {cy + r1 * math.sin(a0):.1f} '
             f'A{r1:.1f} {r1:.1f} 0 0 1 {cx + r1 * math.cos(a1):.1f} {cy + r1 * math.sin(a1):.1f} '
             f'L{cx + r0 * math.cos(a1):.1f} {cy + r0 * math.sin(a1):.1f} A{r0:.1f} {r0:.1f} 0 0 0 {cx + r0 * math.cos(a0):.1f} {cy + r0 * math.sin(a0):.1f} Z')
        s.append(f'<path d="{p}" fill="#5A3A28" opacity=".55"/>')
    s.append(f'<circle cx="{cx}" cy="{cy}" r="{r * .9:.1f}" fill="none" stroke="url(#gold)" stroke-width="{r * .16:.1f}" opacity=".9"/>')
    return ''.join(s)


def _screw(x, y, r=9, rot=30):
    a = math.radians(rot)
    return (f'<circle cx="{x}" cy="{y}" r="{r}" fill="url(#blue)" stroke="#1B2A55" stroke-width="1"/>'
            f'<line x1="{x - r * .8 * math.cos(a):.1f}" y1="{y - r * .8 * math.sin(a):.1f}" x2="{x + r * .8 * math.cos(a):.1f}" '
            f'y2="{y + r * .8 * math.sin(a):.1f}" stroke="#0E1530" stroke-width="2.2"/>')


def plate_svg(label: str = '') -> str:
    """The movement without its jewels: 600 x 600."""
    g = []
    g.append('<defs>'
             f'<radialGradient id="plate" cx="40%" cy="35%" r="75%"><stop offset="0" stop-color="{PLATE[0]}"/><stop offset="1" stop-color="{PLATE[1]}"/></radialGradient>'
             f'<linearGradient id="gold" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{GOLD[0]}"/><stop offset="1" stop-color="{GOLD[1]}"/></linearGradient>'
             f'<radialGradient id="steel" cx="35%" cy="30%" r="80%"><stop offset="0" stop-color="{STEEL[0]}"/><stop offset="1" stop-color="{STEEL[1]}"/></radialGradient>'
             f'<radialGradient id="blue" cx="35%" cy="30%" r="80%"><stop offset="0" stop-color="#6E8FE0"/><stop offset="1" stop-color="{BLUE}"/></radialGradient>'
             '<pattern id="geneve" width="44" height="44" patternUnits="userSpaceOnUse" patternTransform="rotate(-28)">'
             '<rect width="44" height="22" fill="#FFFFFF" opacity=".10"/><rect y="22" width="44" height="22" fill="#000000" opacity=".06"/></pattern>'
             '<pattern id="perlage" width="16" height="16" patternUnits="userSpaceOnUse"><circle cx="8" cy="8" r="7" fill="none" stroke="#FFFFFF" stroke-width="1" opacity=".12"/></pattern>'
             '<filter id="sh" x="-10%" y="-10%" width="120%" height="120%"><feDropShadow dx="2" dy="4" stdDeviation="4" flood-color="#000" flood-opacity=".45"/></filter>'
             '</defs>')
    # the main plate and its perlage
    g.append(f'<circle cx="300" cy="300" r="292" fill="#3A2A22"/><circle cx="300" cy="300" r="284" fill="url(#plate)"/>'
             f'<circle cx="300" cy="300" r="284" fill="url(#perlage)"/>')
    # wheels that sit under the bridges (third, fourth, escape) and the balance
    g.append(_wheel(392, 232, 62, 60))
    g.append(_wheel(440, 372, 56, 56))
    g.append(f'<path d="{_teeth(378, 452, 34, 15, 9)}" fill="url(#steel)" stroke="#555" stroke-width="1"/>')     # escape wheel
    # balance wheel, its arms and the blued hairspring
    g.append('<circle cx="176" cy="418" r="96" fill="none" stroke="url(#gold)" stroke-width="13" filter="url(#sh)"/>')
    for k in range(3):
        a = 2 * math.pi * k / 3 + .4
        g.append(f'<line x1="176" y1="418" x2="{176 + 92 * math.cos(a):.1f}" y2="{418 + 92 * math.sin(a):.1f}" stroke="url(#gold)" stroke-width="7"/>')
    spiral = ' '.join(f'{176 + (14 + 6.5 * t / 6.28) * math.cos(t):.1f},{418 + (14 + 6.5 * t / 6.28) * math.sin(t):.1f}' for t in [i * .15 for i in range(0, 380)])
    g.append(f'<polyline points="{spiral}" fill="none" stroke="{BLUE}" stroke-width="1.3" opacity=".85"/>')
    # barrel bridge with Geneva stripes, the steel ratchet wheel and its sunburst
    bb = 'M70 250 C60 120 150 52 262 60 C350 66 392 130 360 190 C330 248 262 252 226 300 C190 348 92 352 70 250 Z'
    g.append(f'<path d="{bb}" fill="url(#plate)" stroke="#7A4A33" stroke-width="2" filter="url(#sh)"/><path d="{bb}" fill="url(#geneve)"/>')
    g.append(f'<path d="{_teeth(206, 206, 96, 72, 7)}" fill="url(#steel)" stroke="#666" stroke-width="1" filter="url(#sh)"/>')
    g.append(''.join(f'<line x1="206" y1="206" x2="{206 + 84 * math.cos(math.radians(d)):.1f}" y2="{206 + 84 * math.sin(math.radians(d)):.1f}" stroke="#FFFFFF" stroke-width=".6" opacity=".35"/>'
                     for d in range(0, 360, 4)))
    g.append(f'<path d="{_teeth(300, 122, 30, 20, 6)}" fill="url(#steel)" stroke="#666" stroke-width="1"/>')   # crown wheel
    # train bridge, pallet bridge, balance cock
    tb = 'M268 262 C300 238 360 214 410 206 C452 200 488 232 486 288 C484 350 470 404 420 430 C380 450 340 446 330 418 C318 388 360 372 372 344 C384 316 330 330 300 336 C270 342 248 290 268 262 Z'
    g.append(f'<path d="{tb}" fill="url(#plate)" stroke="#7A4A33" stroke-width="2" filter="url(#sh)"/><path d="{tb}" fill="url(#geneve)"/>')
    pb = 'M262 492 C250 470 270 446 300 450 C326 454 346 470 336 492 C328 512 278 514 262 492 Z'
    g.append(f'<path d="{pb}" fill="url(#plate)" stroke="#7A4A33" stroke-width="2" filter="url(#sh)"/>')
    ck = 'M52 530 C40 506 60 486 92 482 C122 478 150 446 164 420 C172 404 196 402 202 420 C208 440 186 462 160 478 C126 500 96 544 52 530 Z'
    g.append(f'<path d="{ck}" fill="url(#plate)" stroke="#7A4A33" stroke-width="2" filter="url(#sh)"/><path d="{ck}" fill="url(#geneve)"/>')
    g.append('<line x1="176" y1="418" x2="118" y2="480" stroke="url(#steel)" stroke-width="4"/>')                # regulator index
    for (x, y, r) in [(110, 120, 10), (340, 150, 9), (118, 300, 9), (470, 300, 9), (404, 420, 9), (280, 280, 8), (318, 498, 8), (76, 510, 8)]:
        g.append(_screw(x, y, r, rot=(x * 7 + y) % 180))
    if label:
        g.append(f'<text x="420" y="292" font-family="Inter Tight, sans-serif" font-size="17" font-weight="700" fill="#F6E3C9" '
                 f'opacity=".85" text-anchor="middle" transform="rotate(-62 420 292)" letter-spacing="2">{label}</text>')
    return _unique('<svg viewBox="0 0 600 600" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">' + ''.join(g) + '</svg>')


def jewel_svg(gold_ring: bool = False) -> str:
    """One jewel in its chaton: 40 x 40."""
    ring = '#F2D58A' if not gold_ring else '#FFE7A0'
    halo = '<circle cx="20" cy="20" r="19" fill="none" stroke="#F2D58A" stroke-width="2.5" opacity=".9"/>' if gold_ring else ''
    return _unique('<svg viewBox="0 0 40 40" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg"><defs>'
                   '<radialGradient id="rb" cx="35%" cy="30%" r="70%"><stop offset="0" stop-color="#FF7A9A"/><stop offset=".5" stop-color="#C21F4A"/>'
                   '<stop offset="1" stop-color="#5E0A22"/></radialGradient></defs>' + halo +
                   f'<circle cx="20" cy="20" r="14" fill="{ring}" stroke="#7A5A22" stroke-width="1"/>'
                   '<circle cx="20" cy="20" r="9.5" fill="url(#rb)"/><circle cx="17" cy="17" r="2.6" fill="#FFFFFF" opacity=".75"/>'
                   '<circle cx="20" cy="20" r="2" fill="#2A0610"/></svg>')
