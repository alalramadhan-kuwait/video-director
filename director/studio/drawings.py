"""Drawings that draw themselves, for an opening that hooks: pencil lines laid down stroke by stroke, then the subject
comes alive (a dial glows, a torpedo glides past). Generic illustrations of the idea, never a copy of a real product's
design and never presented as a photograph.

Each subject is a list of sketch paths and texts on a 560 x 560 card (the `sketch` element of the engine).
"""
from __future__ import annotations

LUME = '#BFF5C2'


def watch(t0=0.0):
    """A generic diver's watch: cushion case, bezel, dial, markers, crown, hands; numerals that glow later."""
    p = []
    case = 'M120 110 Q 280 78 440 110 Q 472 280 440 450 Q 280 482 120 450 Q 88 280 120 110 Z'
    p.append({'d': case, 'at': t0, 'dur': .9, 'width': 3.2, 'fill': '#1A1C1E', 'fillAt': t0 + 1.0, 'fillDur': .6, 'fillOpacity': .9})
    p.append({'d': 'M190 104 L196 30 L364 30 L370 104 M190 456 L196 530 L364 530 L370 456', 'at': t0 + .4, 'dur': .7, 'width': 2.6})
    p.append({'d': 'M130 280 A150 150 0 1 0 430 280 A150 150 0 1 0 130 280', 'at': t0 + .7, 'dur': .7, 'width': 2.8})
    p.append({'d': 'M152 280 A128 128 0 1 0 408 280 A128 128 0 1 0 152 280', 'at': t0 + 1.0, 'dur': .6, 'width': 2.0,
              'fill': '#0E1110', 'fillAt': t0 + 1.4, 'fillDur': .5, 'fillOpacity': 1})
    import math
    marks = ''.join(f'M{280 + 112 * math.sin(a):.0f} {280 - 112 * math.cos(a):.0f} L{280 + 124 * math.sin(a):.0f} {280 - 124 * math.cos(a):.0f} '
                    for a in [i * math.pi / 6 for i in range(12) if i % 3])
    p.append({'d': marks, 'at': t0 + 1.4, 'dur': .5, 'width': 3, 'stroke': LUME, 'opacity': .85})
    p.append({'d': 'M440 262 L474 262 L474 298 L440 298', 'at': t0 + 1.2, 'dur': .4, 'width': 2.6})
    p.append({'d': 'M280 280 L280 186 M280 280 L344 306', 'at': t0 + 1.8, 'dur': .4, 'width': 5, 'stroke': LUME})
    texts = [{'text': n, 'x': x, 'y': y, 'size': 44, 'at': t0 + 1.9 + i * .12, 'dur': .3, 'anchor': 'middle', 'color': LUME, 'font': 'title'}
             for i, (n, x, y) in enumerate((('12', 280, 200), ('3', 384, 296), ('6', 280, 394), ('9', 176, 296)))]
    return p, texts


def torpedo_svg(color='#46555B'):
    """A human torpedo with its two riders, as a silhouette; two small glowing points are their wrists."""
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="420" height="120" viewBox="0 0 420 120">'
            f'<path d="M20 70 Q 30 50 90 50 L330 50 Q 380 52 392 70 Q 380 88 330 90 L90 90 Q 30 90 20 70 Z" fill="{color}" stroke="#8FA3AA" stroke-width="2"/>'
            f'<path d="M392 70 L414 56 L414 84 Z" fill="{color}"/>'
            f'<path d="M150 52 Q 160 18 182 20 Q 196 22 196 40 L196 52 Z M250 52 Q 260 14 282 16 Q 298 18 298 38 L298 52 Z" fill="{color}"/>'
            f'<circle cx="176" cy="44" r="3.5" fill="{LUME}"/><circle cx="278" cy="40" r="3.5" fill="{LUME}"/></svg>')


SUBJECTS = {'watch': watch}
