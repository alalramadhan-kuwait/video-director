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

# The train, laid out so it could run (Bu Khaled): each wheel's pivot at its radius plus the next pinion from the
# one it drives. Barrel (ratchet) 205,205 → centre 300,300 → third 380,248 (r 58) → fourth 430,300 (r 50, 72 from
# the third) → escape 420,358 (r 32, 59 from the fourth) → pallet 378,385 (50 from the escape) → balance 310,435
# (84 from the pallet, 1.7 times). The back shows six jewels, each in its bridge or cock (never on the ratchet or
# crown wheel, never on bare plate: the owner, «المستهدف ناس تعرف بالساعات»).
CENTRE, THIRD, FOURTH, ESCAPE, PALLET, BALANCE = (300, 300), (380, 248), (430, 300), (420, 358), (378, 385), (310, 435)
VISIBLE = [CENTRE, THIRD, FOURTH, ESCAPE, PALLET, BALANCE]
# a 21: cap jewels on the escape wheel and the pallet fork, one each side (PWDB, breitlingsource); the back shows two
CAPS = [ESCAPE, PALLET]
EXTRA = CAPS


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


def _club_teeth(cx, cy, r, n=15):
    """A Swiss lever escape wheel: n club teeth leaning the way it turns."""
    pts = []
    for i in range(n):
        a0 = 2 * math.pi * i / n
        for (da, rr) in ((0, r * .62), (.06, r * .62), (.17, r), (.25, r * .97), (.29, r * .66)):
            a = a0 + da
            pts.append(f'{cx + rr * math.cos(a):.1f},{cy + rr * math.sin(a):.1f}')
    return 'M' + ' L'.join(pts) + ' Z'


def _spiral(cx, cy, r0, r1, turns, start=0.0):
    k = (r1 - r0) / (turns * 2 * math.pi)
    return ' '.join(f'{cx + (r0 + k * t) * math.cos(t + start):.1f},{cy + (r0 + k * t) * math.sin(t + start):.1f}'
                    for t in [i * .08 for i in range(int(turns * 2 * math.pi / .08) + 1)])


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
    g.append('<circle cx="300" cy="300" r="292" fill="#3A2A22"/><circle cx="300" cy="300" r="284" fill="url(#plate)"/>'
             '<circle cx="300" cy="300" r="284" fill="url(#perlage)"/>')
    # winding stem, at the edge in line with the crown wheel
    g.append('<rect x="288" y="8" width="12" height="88" rx="4" fill="url(#steel)" stroke="#555" stroke-width="1"/>')
    # the train under its bridge: centre, third, fourth (gold, with spokes), the steel escape wheel
    g.append(_wheel(*CENTRE, 72, 80))
    g.append(_wheel(*THIRD, 58, 64))
    g.append(_wheel(*FOURTH, 50, 60))
    g.append(f'<path d="{_club_teeth(*ESCAPE, 32)}" fill="url(#steel)" stroke="#555" stroke-width="1"/>'
             f'<circle cx="{ESCAPE[0]}" cy="{ESCAPE[1]}" r="12" fill="url(#steel)" stroke="#555" stroke-width="1"/>')
    # barrel bridge with Geneva stripes; the ratchet and crown wheels on it, the click and its spring
    bb = 'M70 250 C60 120 150 52 262 60 C350 66 392 130 360 190 C330 248 262 252 226 300 C190 348 92 352 70 250 Z'
    g.append(f'<path d="{bb}" fill="url(#plate)" stroke="#7A4A33" stroke-width="2" filter="url(#sh)"/><path d="{bb}" fill="url(#geneve)"/>')
    g.append(f'<path d="{_teeth(205, 205, 90, 72, 7)}" fill="url(#steel)" stroke="#666" stroke-width="1" filter="url(#sh)"/>')
    g.append(''.join(f'<line x1="205" y1="205" x2="{205 + 80 * math.cos(math.radians(d)):.1f}" y2="{205 + 80 * math.sin(math.radians(d)):.1f}" stroke="#FFFFFF" stroke-width=".6" opacity=".35"/>'
                     for d in range(0, 360, 4)))
    g.append(_screw(205, 205, 14, rot=20))                                            # the ratchet screw (no jewel there)
    g.append(f'<path d="{_teeth(294, 127, 30, 20, 6)}" fill="url(#steel)" stroke="#666" stroke-width="1"/>' + _screw(294, 127, 8, rot=70))   # teeth in mesh with the ratchet
    g.append('<path d="M98 262 L130 250 L140 262 L112 276 Z" fill="url(#steel)" stroke="#555" stroke-width="1"/>'      # the click
             '<path d="M112 276 C100 296 84 300 78 286" fill="none" stroke="url(#steel)" stroke-width="3"/>' + _screw(108, 266, 5, rot=10))
    # train bridge over centre, third, fourth and escape; the pallet bridge
    tb = ('M262 290 C262 262 300 242 340 224 C380 204 424 206 448 236 C470 262 470 300 460 330 C452 356 446 384 420 392 '
          'C396 398 384 380 392 360 C398 342 380 328 356 330 C330 332 300 336 284 324 C268 314 262 302 262 290 Z')
    g.append(f'<path d="{tb}" fill="url(#plate)" stroke="#7A4A33" stroke-width="2" filter="url(#sh)"/><path d="{tb}" fill="url(#geneve)"/>')
    pb = 'M352 384 C352 366 372 360 390 366 C410 372 414 392 402 404 C388 416 356 410 352 384 Z'
    g.append(f'<path d="{pb}" fill="url(#plate)" stroke="#7A4A33" stroke-width="2" filter="url(#sh)"/>')
    # balance wheel with its three arms (above the pallet bridge, under the cock: Bu Khaled)
    bx, by = BALANCE
    g.append(f'<circle cx="{bx}" cy="{by}" r="76" fill="none" stroke="url(#gold)" stroke-width="11" filter="url(#sh)"/>')
    for k in range(3):
        an = 2 * math.pi * k / 3 + .9
        g.append(f'<line x1="{bx}" y1="{by}" x2="{bx + 72 * math.cos(an):.1f}" y2="{by + 72 * math.sin(an):.1f}" stroke="url(#gold)" stroke-width="6"/>')
    # the hairspring under the cock: a steel-grey spiral of eleven turns from its collet to the stud
    g.append(f'<polyline points="{_spiral(bx, by, 7, 44, 11, 0)}" fill="none" stroke="#C9CDD2" stroke-width="1.1" opacity=".95"/>')
    # the balance cock: a broad teardrop from the balance to its foot, one screw; the spring shows around its head
    ck = f'M{bx - 24} {by - 4} C{bx - 24} {by - 34} {bx + 24} {by - 34} {bx + 24} {by - 4} C{bx + 24} {by + 22} 268 500 246 526 C230 544 200 540 200 520 C200 500 {bx - 24} {by + 22} {bx - 24} {by - 4} Z'
    g.append(f'<path d="{ck}" fill="url(#plate)" stroke="#7A4A33" stroke-width="2" filter="url(#sh)"/><path d="{ck}" fill="url(#geneve)"/>')
    # hairspring: a steel-grey spiral, its outer end pinned at the stud; the regulator index and its +/- scale
    g.append(f'<rect x="{bx - 50}" y="{by - 4}" width="10" height="9" fill="url(#steel)" stroke="#555" stroke-width=".8"/>')              # stud, at the spring's outer end
    g.append(f'<path d="M{bx} {by} L{bx - 40} {by + 26} L{bx - 92} {by + 70}" fill="none" stroke="url(#steel)" stroke-width="4" stroke-linecap="round"/>'
             f'<circle cx="{bx - 40}" cy="{by + 26}" r="3" fill="#555"/>')                                                               # regulator index
    g.append(f'<text x="{bx - 108}" y="{by + 66}" font-family="Inter Tight, sans-serif" font-size="13" fill="#F6E3C9" opacity=".8">−</text>'
             f'<text x="{bx - 84}" y="{by + 90}" font-family="Inter Tight, sans-serif" font-size="13" fill="#F6E3C9" opacity=".8">+</text>')
    for (x, y, r) in [(110, 120, 10), (340, 150, 9), (118, 300, 9), (452, 252, 9), (440, 372, 8), (282, 316, 8), (372, 404, 7), (222, 528, 9)]:
        g.append(_screw(x, y, r, rot=(x * 7 + y) % 180))
    if label:
        g.append(f'<text x="352" y="276" font-family="Inter Tight, sans-serif" font-size="15" font-weight="700" fill="#F6E3C9" '
                 f'opacity=".85" text-anchor="middle" transform="rotate(-24 352 276)" letter-spacing="2">{label}</text>')
    return _unique('<svg viewBox="0 0 600 600" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">' + ''.join(g) + '</svg>')


def balance_cap_svg() -> str:
    """The balance jewel with its cap jewel held by a lyre spring (shock protection), as every 17 has it: 40 x 40."""
    return _unique('<svg viewBox="0 0 40 40" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg"><defs>'
                   '<radialGradient id="rb" cx="35%" cy="30%" r="70%"><stop offset="0" stop-color="#FF7A9A"/><stop offset=".5" stop-color="#C21F4A"/>'
                   '<stop offset="1" stop-color="#5E0A22"/></radialGradient></defs>'
                   '<circle cx="20" cy="20" r="13" fill="#E9B596" stroke="#7A4A33" stroke-width=".8"/>'
                   '<circle cx="20" cy="20" r="9" fill="url(#rb)"/>'
                   '<circle cx="20" cy="20" r="6.5" fill="#DDEBFF" opacity=".55" stroke="#FFFFFF" stroke-width=".6"/>'
                   '<path d="M6 20 C6 8 16 4 20 11 C24 4 34 8 34 20" fill="none" stroke="#EEF0F2" stroke-width="2.4" stroke-linecap="round"/>'
                   '<path d="M6 20 C6 32 16 36 20 29 C24 36 34 32 34 20" fill="none" stroke="#EEF0F2" stroke-width="2.4" stroke-linecap="round"/></svg>')


def cap_svg() -> str:
    """A cap jewel's setting seen from above: a small polished steel plate held by two screws, the capstone at its
    centre, ringed in gold to mark it as one of a 21's four: 40 x 40."""
    return _unique('<svg viewBox="0 0 40 40" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg"><defs>'
                   '<radialGradient id="cp" cx="35%" cy="30%" r="80%"><stop offset="0" stop-color="#F4F5F6"/><stop offset="1" stop-color="#8E949B"/></radialGradient>'
                   '<radialGradient id="rb" cx="35%" cy="30%" r="70%"><stop offset="0" stop-color="#FF7A9A"/><stop offset=".5" stop-color="#C21F4A"/>'
                   '<stop offset="1" stop-color="#5E0A22"/></radialGradient></defs>'
                   '<circle cx="20" cy="20" r="19" fill="none" stroke="#F2D58A" stroke-width="2.4"/>'
                   '<rect x="4" y="13" width="32" height="14" rx="7" fill="url(#cp)" stroke="#555" stroke-width=".8"/>'
                   '<circle cx="8.5" cy="20" r="2.6" fill="#2F4F9C"/><circle cx="31.5" cy="20" r="2.6" fill="#2F4F9C"/>'
                   '<circle cx="20" cy="20" r="6" fill="url(#rb)"/><circle cx="18.2" cy="18.2" r="1.6" fill="#FFFFFF" opacity=".8"/></svg>')


def jewel_svg(gold_ring: bool = False) -> str:
    """One jewel pressed into its bridge, in its polished sink (no gold chaton: an honest, everyday movement): 40 x 40."""
    return _unique('<svg viewBox="0 0 40 40" width="100%" height="100%" xmlns="http://www.w3.org/2000/svg"><defs>'
                   '<radialGradient id="rb" cx="35%" cy="30%" r="70%"><stop offset="0" stop-color="#FF7A9A"/><stop offset=".5" stop-color="#C21F4A"/>'
                   '<stop offset="1" stop-color="#5E0A22"/></radialGradient></defs>'
                   '<circle cx="20" cy="20" r="13" fill="#E9B596" stroke="#7A4A33" stroke-width=".8"/>'
                   '<circle cx="20" cy="20" r="9.5" fill="url(#rb)"/><circle cx="17" cy="17" r="2.4" fill="#FFFFFF" opacity=".7"/>'
                   '<circle cx="20" cy="20" r="2" fill="#2A0610"/></svg>')
