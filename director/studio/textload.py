"""How much there is to read at once. The owner: «the video have more than 3 lines of words, it is hard to read for
the viewers. caption, title, sub title. it is too much».

On screen at any moment: the spoken captions and ONE more block of words (the scene's title banner, OR its card,
OR its line). A scene with its own card or line shows its banner first, alone, and the banner leaves before the card
comes in; when the card comes in too early for that, the scene has no banner. A photo's small credit line is not a
block of words."""
from __future__ import annotations

BANNER_AT = 0.25          # paper.js: the banner comes in 0.25 s after the cut
BANNER_MIN = 1.6          # s: the shortest a banner is worth showing on its own
BANNER_GAP = 0.3          # s: it leaves this long before the card or line comes in
SMALL = 20                # px: text this size or smaller is a credit or a source note, not a block to read


def _in_at(e: dict) -> float:
    i = e.get('in')
    return float(i.get('at', 0)) if isinstance(i, dict) else 0.0


def blocks(sc: dict) -> list[dict]:
    """The scene's own blocks of words besides the banner and the captions: cards and text bigger than a credit."""
    out = []
    for e in sc.get('elements', []):
        if e.get('type') == 'card' or (e.get('type') == 'text' and float(e.get('size') or 0) > SMALL):
            out.append(e)
    return out


def budget(sc: dict) -> str | None:
    """Fits the scene to captions + one block: sets `bannerOut` (the banner leaves before the first card or line) or
    drops the banner. Returns what it did, or None."""
    if not sc.get('banner'): return None
    bs = blocks(sc)
    if not bs: return None
    first = min(_in_at(e) for e in bs)
    leave = round(first - BANNER_GAP, 2)
    if leave - BANNER_AT >= BANNER_MIN:
        sc['bannerOut'] = leave
        return f"{sc.get('id')}: the banner leaves at {leave} s, before its card or line"
    sc['banner'] = None
    sc.pop('bannerOut', None)
    return f"{sc.get('id')}: no banner (its card or line comes in at {first} s)"


def fit(scenes: list[dict]) -> list[str]:
    return [n for n in (budget(sc) for sc in scenes if not sc.get('endcard')) if n]
