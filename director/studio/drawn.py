"""Paper-cut drawings in the Time Keeper style, for a watch or a person the story names but no free photograph shows
whole (rule 12h). Flat pieces of coloured paper, layered with a soft shadow under each, in the brand's restrained
colours: steel, brass, black, cream, leather. No cartoon faces (the owner finds cartoons childish): a person is a
figure of cut paper with the clothes of the time, and every drawing is labelled as one on screen.

watch(kind, ...)   'radiomir' (the 1936 cushion case: wire lugs, onion crown, 12 3 6 9), 'luminor' (cushion case and
                   the crown-guard bridge), 'oyster' (the 1926 octagon, Roman numerals, small seconds), 'round'
person(kind, ...)  'man_suit', 'woman_dress', 'worker' (a dial painter's smock), 'diver' (a combat swimmer's rubber
                   suit and mask), 'scientist' (a lab coat)
Each returns (svg, width, height) in drawing units; the template scales it.
"""
from __future__ import annotations
import math

PAPER = '#F3F0E8'
STEEL, STEEL_D, BRASS, BRASS_D = '#BFC3C9', '#8E949B', '#C9A35F', '#8F6F37'
BLACK, CREAM, LEATHER, LEATHER_D, LUME = '#151515', '#EFE7D2', '#6E4B2C', '#4E331D', '#E6DCB8'


def _defs(uid: str) -> str:
    return (f'<defs><filter id="{uid}" x="-20%" y="-20%" width="140%" height="140%">'
            f'<feDropShadow dx="1.6" dy="3.2" stdDeviation="2.2" flood-color="#000" flood-opacity=".34"/></filter></defs>')


def _cushion(cx, cy, r, k=0.82):
    """A cushion: a square with bulging sides and round corners (Radiomir, Luminor)."""
    a, b = r, r * k
    return (f'M{cx - b},{cy - a} Q{cx},{cy - a * 1.08} {cx + b},{cy - a} Q{cx + a},{cy - a} {cx + a},{cy - b} '
            f'Q{cx + a * 1.08},{cy} {cx + a},{cy + b} Q{cx + a},{cy + a} {cx + b},{cy + a} Q{cx},{cy + a * 1.08} {cx - b},{cy + a} '
            f'Q{cx - a},{cy + a} {cx - a},{cy + b} Q{cx - a * 1.08},{cy} {cx - a},{cy - b} Q{cx - a},{cy - a} {cx - b},{cy - a}Z')


def _octagon(cx, cy, r):
    pts = [(cx + r * math.cos(math.radians(22.5 + 45 * i)), cy + r * math.sin(math.radians(22.5 + 45 * i))) for i in range(8)]
    return 'M' + ' L'.join(f'{x:.1f},{y:.1f}' for x, y in pts) + 'Z'


def _hands(cx, cy, r, color, hm=(10, 10)):
    h, m = hm
    ah, am = math.radians(30 * (h % 12) + m / 2 - 90), math.radians(6 * m - 90)
    def sword(a, ln, w):
        x, y = cx + ln * math.cos(a), cy + ln * math.sin(a)
        nx, ny = -math.sin(a) * w, math.cos(a) * w
        return f'<path d="M{cx + nx:.1f},{cy + ny:.1f} L{x:.1f},{y:.1f} L{cx - nx:.1f},{cy - ny:.1f}Z" fill="{color}"/>'
    return sword(ah, r * .5, r * .07) + sword(am, r * .74, r * .055) + f'<circle cx="{cx}" cy="{cy}" r="{r * .06:.1f}" fill="{color}"/>'


def watch(kind: str = 'radiomir', uid: str = 'pw') -> tuple[str, int, int]:
    W, H, cx, cy, r = 400, 820, 200, 410, 150
    sh = f'filter="url(#{uid})"'
    p = [_defs(uid)]
    strap = LEATHER if kind != 'oyster' else BLACK
    for y0, y1 in ((20, cy - r * .7), (cy + r * .7, H - 20)):                     # the strap, with its stitching
        p.append(f'<rect x="{cx - 82}" y="{y0}" width="164" height="{y1 - y0}" rx="26" fill="{strap}" {sh}/>')
        p.append(f'<rect x="{cx - 70}" y="{y0 + 12}" width="140" height="{y1 - y0 - 24}" rx="20" fill="none" stroke="{CREAM}" '
                 f'stroke-opacity=".55" stroke-width="2.2" stroke-dasharray="7 6"/>')
    if kind in ('radiomir', 'luminor'):
        if kind == 'radiomir':                                                   # wire lugs
            for s in (-1, 1):
                p.append(f'<path d="M{cx - 70},{cy + s * r * .86} L{cx - 70},{cy + s * (r + 40)} L{cx + 70},{cy + s * (r + 40)} '
                         f'L{cx + 70},{cy + s * r * .86}" fill="none" stroke="{STEEL}" stroke-width="11" stroke-linejoin="round" {sh}/>')
            p.append(f'<circle cx="{cx + r + 18}" cy="{cy}" r="22" fill="{STEEL}" {sh}/>')          # the onion crown
            for i in range(-3, 4):
                p.append(f'<line x1="{cx + r + 4}" y1="{cy + i * 6}" x2="{cx + r + 36}" y2="{cy + i * 6}" stroke="{STEEL_D}" stroke-width="2"/>')
        else:                                                                     # Luminor: lugs in the case, the crown guard
            p.append(f'<path d="M{cx + r * .55},{cy - 62} Q{cx + r + 62},{cy - 70} {cx + r + 58},{cy} Q{cx + r + 62},{cy + 70} '
                     f'{cx + r * .55},{cy + 62}Z" fill="{STEEL}" {sh}/>')
            p.append(f'<rect x="{cx + r + 14}" y="{cy - 18}" width="26" height="36" rx="6" fill="{STEEL_D}" {sh}/>')
            p.append(f'<path d="M{cx + r + 38},{cy - 40} L{cx + r + 64},{cy - 10} L{cx + r + 58},{cy + 4}" fill="none" stroke="{STEEL_D}" '
                     f'stroke-width="9" stroke-linecap="round" {sh}/>')
        p.append(f'<path d="{_cushion(cx, cy, r + 6)}" fill="{STEEL_D}" {sh}/>')
        p.append(f'<path d="{_cushion(cx, cy, r)}" fill="{STEEL}"/>')
        p.append(f'<path d="{_cushion(cx, cy, r * .82)}" fill="{BLACK}" {sh}/>')
        for i, t in ((0, '12'), (3, '3'), (6, '6'), (9, '9')):                    # the big luminous numerals
            a = math.radians(30 * i - 90); x, y = cx + r * .58 * math.cos(a), cy + r * .58 * math.sin(a)
            p.append(f'<text x="{x:.1f}" y="{y + 15:.1f}" font-family="Inter Tight, Cairo, sans-serif" font-weight="900" font-size="44" '
                     f'text-anchor="middle" fill="{LUME}">{t}</text>')
        for i in (1, 2, 4, 5, 7, 8, 10, 11):
            a = math.radians(30 * i - 90)
            p.append(f'<circle cx="{cx + r * .62 * math.cos(a):.1f}" cy="{cy + r * .62 * math.sin(a):.1f}" r="7" fill="{LUME}"/>')
        p.append(_hands(cx, cy, r * .8, LUME))
    elif kind == 'oyster':
        p.append(f'<rect x="{cx - 60}" y="{cy - r - 34}" width="120" height="44" rx="8" fill="{BRASS_D}" {sh}/>')
        p.append(f'<rect x="{cx - 60}" y="{cy + r - 10}" width="120" height="44" rx="8" fill="{BRASS_D}" {sh}/>')
        p.append(f'<rect x="{cx + r - 6}" y="{cy - 16}" width="34" height="32" rx="7" fill="{BRASS}" {sh}/>')
        p.append(f'<path d="{_octagon(cx, cy, r + 12)}" fill="{BRASS_D}" {sh}/>')
        p.append(f'<path d="{_octagon(cx, cy, r + 2)}" fill="{BRASS}"/>')
        for i in range(48):                                                         # the fluted bezel
            a = math.radians(i * 7.5)
            p.append(f'<line x1="{cx + r * .9 * math.cos(a):.1f}" y1="{cy + r * .9 * math.sin(a):.1f}" x2="{cx + r * .99 * math.cos(a):.1f}" '
                     f'y2="{cy + r * .99 * math.sin(a):.1f}" stroke="{BRASS_D}" stroke-width="3"/>')
        p.append(f'<circle cx="{cx}" cy="{cy}" r="{r * .82}" fill="{PAPER}" {sh}/>')
        for i, t in enumerate(['XII', 'I', 'II', 'III', 'IIII', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI']):
            if i == 6: continue
            a = math.radians(30 * i - 90); x, y = cx + r * .66 * math.cos(a), cy + r * .66 * math.sin(a)
            p.append(f'<text x="{x:.1f}" y="{y + 8:.1f}" font-family="Georgia, serif" font-weight="700" font-size="{22 if len(t) > 2 else 26}" '
                     f'text-anchor="middle" fill="{BLACK}">{t}</text>')
        p.append(f'<circle cx="{cx}" cy="{cy + r * .42}" r="{r * .2}" fill="none" stroke="{BLACK}" stroke-width="2"/>')   # small seconds
        p.append(_hands(cx, cy, r * .78, BLACK))
    else:
        p.append(f'<circle cx="{cx}" cy="{cy}" r="{r + 8}" fill="{STEEL_D}" {sh}/><circle cx="{cx}" cy="{cy}" r="{r}" fill="{STEEL}"/>')
        p.append(f'<circle cx="{cx}" cy="{cy}" r="{r * .84}" fill="{BLACK}" {sh}/>')
        for i in range(12):
            a = math.radians(30 * i - 90)
            p.append(f'<rect x="{cx + r * .68 * math.cos(a) - 4:.1f}" y="{cy + r * .68 * math.sin(a) - 12:.1f}" width="8" height="24" '
                     f'fill="{LUME}" transform="rotate({30 * i} {cx + r * .68 * math.cos(a):.1f} {cy + r * .68 * math.sin(a):.1f})"/>')
        p.append(_hands(cx, cy, r * .82, LUME))
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">' + ''.join(p) + '</svg>', W, H


DRESS = {
    'man_suit': {'top': '#2B2F36', 'bottom': '#2B2F36', 'hair': '#2A211B', 'shoes': '#151515', 'shirt': PAPER, 'hat': True},
    'woman_dress': {'top': '#5B4A5E', 'bottom': '#5B4A5E', 'hair': '#231A15', 'shoes': '#3A2A22', 'dress': True, 'bob': True},
    'worker': {'top': '#C9BFA8', 'bottom': '#4E4A45', 'hair': '#3B2A1F', 'shoes': '#2A211B', 'dress': True, 'bob': True, 'apron': True},
    'diver': {'top': '#1E2226', 'bottom': '#1E2226', 'hair': None, 'shoes': '#111', 'diver': True},
    'scientist': {'top': PAPER, 'bottom': '#3A3D44', 'hair': '#3A2A1F', 'shoes': '#151515', 'coat': True},
}


def person(kind: str = 'man_suit', uid: str = 'pp') -> tuple[str, int, int]:
    """A standing figure about seven heads tall, faceless, in the clothes of the time."""
    d = DRESS[kind]
    W, H, cx = 300, 900, 150
    sh = f'filter="url(#{uid})"'
    skin = '#D9B89A'
    head, hr = 118, 54
    p = [_defs(uid)]
    p.append(f'<rect x="{cx - 18}" y="{head + hr - 6}" width="36" height="34" fill="{skin}"/>')                # neck
    leg_top, leg_bot = 520, 840
    if d.get('dress'):
        p.append(f'<rect x="{cx - 36}" y="{leg_top + 120}" width="26" height="{leg_bot - leg_top - 120}" rx="10" fill="{skin}" {sh}/>')
        p.append(f'<rect x="{cx + 10}" y="{leg_top + 120}" width="26" height="{leg_bot - leg_top - 120}" rx="10" fill="{skin}" {sh}/>')
        p.append(f'<path d="M{cx - 62},{205} L{cx + 62},{205} L{cx + 98},{leg_top + 140} L{cx - 98},{leg_top + 140}Z" fill="{d["top"]}" {sh}/>')
        if d.get('apron'):
            p.append(f'<path d="M{cx - 44},{300} L{cx + 44},{300} L{cx + 62},{leg_top + 110} L{cx - 62},{leg_top + 110}Z" fill="{PAPER}" opacity=".9" {sh}/>')
    else:
        for s in (-1, 1):
            p.append(f'<rect x="{cx + (8 if s > 0 else -50)}" y="{leg_top - 10}" width="42" height="{leg_bot - leg_top + 10}" rx="12" '
                     f'fill="{d["bottom"]}" {sh}/>')
        p.append(f'<path d="M{cx - 66},{200} L{cx + 66},{200} L{cx + 58},{leg_top + 40} L{cx - 58},{leg_top + 40}Z" fill="{d["top"]}" {sh}/>')
        if d.get('shirt'):
            p.append(f'<path d="M{cx - 16},{200} L{cx + 16},{200} L{cx},{300}Z" fill="{d["shirt"]}"/>'
                     f'<path d="M{cx - 6},{214} L{cx + 6},{214} L{cx + 4},{290} L{cx},{300} L{cx - 4},{290}Z" fill="#6E1E24"/>')
        if d.get('coat'):
            p.append(f'<path d="M{cx - 70},{200} L{cx + 70},{200} L{cx + 74},{leg_top + 140} L{cx - 74},{leg_top + 140}Z" fill="{PAPER}" {sh}/>'
                     f'<line x1="{cx}" y1="{214}" x2="{cx}" y2="{leg_top + 136}" stroke="#C9C3B4" stroke-width="3"/>')
    for s in (-1, 1):                                                            # arms and hands
        x = cx + s * 78
        p.append(f'<rect x="{x - 17}" y="{210}" width="34" height="290" rx="16" fill="{d["top"] if not d.get("coat") else PAPER}" '
                 f'transform="rotate({-s * 4} {x} 210)" {sh}/>')
        p.append(f'<circle cx="{x + s * 14}" cy="{512}" r="17" fill="{skin if not d.get("diver") else "#1E2226"}" {sh}/>')
    for s in (-1, 1):
        p.append(f'<rect x="{cx + (6 if s > 0 else -56)}" y="{leg_bot - 4}" width="50" height="24" rx="11" fill="{d["shoes"]}" {sh}/>')
    p.append(f'<ellipse cx="{cx}" cy="{head}" rx="{hr * .86:.1f}" ry="{hr}" fill="{skin if not d.get("diver") else "#1E2226"}" {sh}/>')
    if d.get('diver'):                                                            # the mask and the breathing set
        p.append(f'<rect x="{cx - 42}" y="{head - 22}" width="84" height="40" rx="16" fill="#8FA7B3" stroke="#C9CCD1" stroke-width="5"/>')
        p.append(f'<rect x="{cx - 54}" y="{240}" width="108" height="110" rx="20" fill="#3A4047" {sh}/>')
        p.append(f'<path d="M{cx - 20},{head + 30} Q{cx},{head + 90} {cx - 40},{250}" fill="none" stroke="#3A4047" stroke-width="10"/>')
    elif d.get('bob'):
        p.append(f'<path d="M{cx - 54},{head + 26} Q{cx - 62},{head - 66} {cx},{head - 62} Q{cx + 62},{head - 66} {cx + 54},{head + 26} '
                 f'L{cx + 40},{head + 30} Q{cx + 40},{head - 26} {cx},{head - 30} Q{cx - 40},{head - 26} {cx - 40},{head + 30}Z" fill="{d["hair"]}" {sh}/>')
    elif d.get('hair'):
        p.append(f'<path d="M{cx - 48},{head - 6} Q{cx - 50},{head - 64} {cx},{head - 60} Q{cx + 50},{head - 64} {cx + 48},{head - 6} '
                 f'Q{cx},{head - 36} {cx - 48},{head - 6}Z" fill="{d["hair"]}" {sh}/>')
    if d.get('hat'):
        p.append(f'<ellipse cx="{cx}" cy="{head - 40}" rx="74" ry="14" fill="#1C1E22" {sh}/>'
                 f'<path d="M{cx - 46},{head - 42} L{cx - 40},{head - 96} Q{cx},{head - 108} {cx + 40},{head - 96} L{cx + 46},{head - 42}Z" fill="#1C1E22" {sh}/>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">' + ''.join(p) + '</svg>', W, H
