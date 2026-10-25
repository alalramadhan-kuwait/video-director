"""Paper-cut drawings of people in the Time Keeper style, for a person the story names but no free photograph shows
whole (rule 12h). Flat pieces of coloured paper, layered with a soft shadow under each, in the brand's restrained
colours. No cartoon faces (the owner finds cartoons childish): a person is a figure of cut paper with the clothes of
the time, and every drawing is labelled as one on screen.

Watches are never drawn (the owner's rule: the films are for collectors, and every case, dial and hand must be the
real one). A watch is shown only in its real photograph: cut out when the photo shows it whole, the photo itself
when it does not.

person(kind, ...)  'man_suit', 'woman_dress', 'worker' (a dial painter's smock), 'diver' (a combat swimmer's rubber
                   suit and mask), 'scientist' (a lab coat)
It returns (svg, width, height) in drawing units; the template scales it.
"""
from __future__ import annotations

PAPER = '#F3F0E8'


def _defs(uid: str) -> str:
    return (f'<defs><filter id="{uid}" x="-20%" y="-20%" width="140%" height="140%">'
            f'<feDropShadow dx="1.6" dy="3.2" stdDeviation="2.2" flood-color="#000" flood-opacity=".34"/></filter></defs>')


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
