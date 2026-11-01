"""Film-wide looks. `look: data` (the owner, on the rubies film: the Altivère video's style, «فيديو Altivère»): one
near-black stage for the whole film, quiet negative space, big numbers in warm sand, facts in mono with « · »
separators, photos as clean flat prints (no tape, no polaroid, no tilt), and one accent colour: the subject itself
(the ruby red). Only the grammar is taken: never another film's frames, script or music. The paper look stays the
default."""
from __future__ import annotations

BG, SAND, INK, RUBY = '#080808', '#B3AA93', '#EDE8DC', '#9B1B30'
MONO = '"JetBrains Mono","Cairo",ui-monospace,monospace'
LOOKS = ('paper', 'data')


def of(film: dict) -> str:
    look = film.get('look', 'paper')
    if look not in LOOKS: raise ValueError(f"look {look!r}: one of {', '.join(LOOKS)}")
    return look


def theme(look: str, theme: str) -> str:
    """The scene's theme under the look: the data stage is always the black one."""
    return 'tk-black' if look == 'data' else theme


def style(look: str, base: dict) -> dict:
    """The storyboard style under the look: a flat banner (no paper, tape or torn edge) in mono sand, dark captions
    with the ruby on the spoken word, no paper grain, a soft vignette."""
    if look != 'data': return base
    if 'style' in base: return {**base, 'style': style(look, base['style'])}      # art.style(brand) is {'style': {...}}
    st = {**base}
    st['banner'] = {**base.get('banner', {}), 'paper': BG, 'ink': SAND, 'tape': 'none', 'torn': 0, 'size': 26,
                    'font': MONO, 'upper': False, 'ls': .06}
    st['caption'] = {**base.get('caption', {}), 'bg': '#141414', 'ink': INK, 'active': '#D9475E', 'activeLight': '#9B1B30'}
    st['grain'], st['vignette'] = 0, .35
    return st


def scene(look: str, sc: dict) -> dict:
    """A scene restyled for the look: prints lie flat and clean, cards are dark with sand words. Returns the scene."""
    if look != 'data': return sc
    sc['theme'] = 'tk-black'
    sc['floor'] = False
    for e in sc.get('elements', []):
        t = e.get('type')
        if t in ('photo', 'image') and not e.get('silhouette'):
            if t == 'photo' or e.get('polaroid'):
                e.update(polaroid=False, frame=False)
            e.pop('tape', None)
            if not isinstance(e.get('rot'), list): e['rot'] = 0
        elif t == 'card':
            e.update(style='dark', color='#111111', ink=SAND, edge='none', tex='flat', rot=0)
            e.pop('tape', None); e.pop('pin', None)
            if e.get('label'): e['labelFont'] = 'ui'
        elif t == 'text' and e.get('paper') and e.get('font') == 'cap':          # a credit line: small, quiet, no paper
            e.update(paper=None, color='#8C8577')
    return sc
