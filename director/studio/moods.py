"""Moods: the feeling of a line, made visible and audible so the viewer feels it with the story.

A film line says `mood: mystery | fear | sadness | tension | joy | wonder`. The mood adds a light grade over the
scene (under the banner and the captions, never hiding the words), and a sound: a low drone for mystery, a heartbeat
for fear, a slow clock for tension, a chime for joy and wonder. The words still have to carry the feeling: the mood
only underlines what the narration says.
"""
from __future__ import annotations

from .sets import uid

W, H = 760, 1320
Z = 800                                    # over the scene, under the banner (900) and the captions (950)


def _svg(body):
    return {'type': 'svg', 'w': W, 'h': H, 'x': 360, 'y': 640, 'z': Z, 'still': True,
            'svg': f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}">{body}</svg>'}


def _vignette(color, inner=.45, edge=.75):
    i = uid('mood')
    return (f'<defs><radialGradient id="{i}" cx="50%" cy="48%" r="70%"><stop offset="{inner}" stop-color="{color}" stop-opacity="0"/>'
            f'<stop offset="1" stop-color="{color}" stop-opacity="{edge}"/></radialGradient></defs><rect width="{W}" height="{H}" fill="url(#{i})"/>')


def _glow(color, cx, cy, op):
    i = uid('mood')
    return (f'<defs><radialGradient id="{i}" cx="{cx}" cy="{cy}" r="60%"><stop offset="0" stop-color="{color}" stop-opacity="{op}"/>'
            f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></radialGradient></defs><rect width="{W}" height="{H}" fill="url(#{i})"/>')


def mystery(dur):
    i = uid('fog')
    fog = {**_svg(f'<defs><linearGradient id="{i}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#9AA3A8" stop-opacity=".10"/>'
                  f'<stop offset=".3" stop-color="#9AA3A8" stop-opacity="0"/><stop offset=".7" stop-color="#9AA3A8" stop-opacity="0"/>'
                  f'<stop offset="1" stop-color="#9AA3A8" stop-opacity=".08"/></linearGradient></defs><rect width="{W}" height="{H}" fill="url(#{i})"/>'),
           'x': [[0, 330], [dur, 390]]}                                    # soft mist at top and bottom, no hard edge
    return [_svg(_vignette('#05070A', .35, .8)), fog], [('drone', -20)], []


def fear(dur):
    pulse = [[k * .95, .35 if k % 2 else .85] for k in range(int(dur / .95) + 2)]
    return [{**_svg(_vignette('#3A0606', .4, .85)), 'opacity': pulse}], [('heartbeat', -16)], []


def sadness(dur):
    return [_svg(f'<rect width="{W}" height="{H}" fill="#3E5260" fill-opacity=".22"/>'), _svg(_vignette('#0C1216', .5, .55))], [('drone', -30)], []


def tension(dur):
    return [_svg(_vignette('#0A0A0A', .4, .7))], [('watch_run', -18)], []


def joy(dur):
    leak = {**_svg(_glow('#F5C77A', '85%', '12%', .55)), 'opacity': [[0, .4], [dur * .5, 1], [dur, .7]]}
    return [leak], [('room', -34)], [(0.25, 'chime', -16)]        # every mood has a bed under the voice (the mix review)


def wonder(dur):
    leak = {**_svg(_glow('#E8EEF2', '50%', '0%', .45)), 'opacity': [[0, .3], [dur, .9]]}
    return [leak, {'type': 'sparkles', 'x': 360, 'y': 520, 'count': 10, 'radius': 120, 'life': 1.4, 'color': '#FFFFFF', 'at': .8, 'z': Z}], \
        [('drone', -34)], [(0.4, 'chime', -20)]


MOODS = {'mystery': mystery, 'fear': fear, 'sadness': sadness, 'tension': tension, 'joy': joy, 'wonder': wonder}
NAME_AR = {'mystery': 'غموض', 'fear': 'رعب', 'sadness': 'حزن', 'tension': 'توتر', 'joy': 'فرح', 'wonder': 'دهشة'}


def dress(sc: dict, mood: str | None, dur: float) -> dict:
    if not mood: return sc
    els, beds, sfx = MOODS[mood](dur)
    sc['elements'] = sc['elements'] + [{**e, 'mood': True} for e in els]      # marked: a clip that replaces the picture keeps the light
    sc.setdefault('beds', []).extend({'name': n, 'gain': g} for n, g in beds)
    sc.setdefault('sfx', []).extend({'at': a, 'name': n, 'gain': g} for a, n, g in sfx if a < dur)
    sc['mood'] = mood
    return sc
