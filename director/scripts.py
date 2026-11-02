"""The script library (brand/script_library.yaml): the types of script that guide a film's video type, and the three
languages a script is written in (Time Keeper style, light Arabic, Kuwaiti), each with its rules and examples.

The owner, 2 Nov 2026: «there are type of scripts… build a library to guide the video type from this script… set the
language of these scripts and have the rules: is it light Arabic or Kuwaiti or TK style, with examples».

A film names them in its file: `script_type: numbers_explainer`, `language: tk` (the brand's default when left out).
`check()` holds the script to them; `estimate()` gives its spoken length before any voice is paid for."""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import yaml

from . import brand as B

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / 'brand/script_library.yaml'
AR = '\u0621-\u064A\u066E-\u06D3'                          # Arabic letters (not ؟ or ،)
# Words that mark a line as Kuwaiti: allowed in Time Keeper style only as a light touch (the hook or the closing
# question, and at most two lines in between), the base of the Kuwaiti language, never in light Arabic.
KUWAITI = ('شنو', 'ليش', 'وايد', 'شلون', 'يبي', 'تبي', 'لين', 'جذي', 'عقب', 'شكم', 'شكثر', 'اللي', 'بس', 'هني')
TK_KUWAITI_LINES = 2


@lru_cache(maxsize=1)
def library() -> dict:
    return yaml.safe_load(LIBRARY.read_text(encoding='utf-8'))


def types() -> dict:
    return library()['types']


def languages() -> dict:
    return library()['languages']


def default_language(brand: str = 'timekeeper') -> str:
    nar = B.load(brand).get('narration') or {}
    return nar.get('script_language') or next(k for k, v in languages().items() if v.get('default'))


def language(film: dict) -> str:
    return film.get('language') or default_language(film.get('brand', 'timekeeper'))


def _has(word: str, text: str) -> bool:
    """The word on its own (or after و / ف), never inside another word."""
    return re.search(rf'(?<![{AR}])[وف]?{re.escape(word)}(?![{AR}])', text) is not None


def _spoken(ln: dict) -> str:
    return ln.get('say') or ln.get('text') or ''


def estimate(film: dict) -> dict:
    """The script's spoken length before any voice is recorded: characters, and seconds at the brand voice's pace
    (`narration.chars_per_second`; Jarnathan reads about 10 a second)."""
    nar = B.load(film.get('brand', 'timekeeper')).get('narration') or {}
    rate = float(nar.get('chars_per_second') or 10)
    chars = sum(len(B.spoken(_spoken(ln), film.get('brand', 'timekeeper'))) for ln in film.get('lines', []))
    return {'chars': chars, 'seconds': round(chars / rate, 1), 'chars_per_second': rate}


def check(film: dict) -> list[str]:
    """What the script breaks of its type and its language. Empty when it keeps them."""
    out, lines = [], film.get('lines', [])
    lang = language(film)
    if lang not in languages():
        return [f"language: {lang!r} is not one of {', '.join(languages())} (brand/script_library.yaml)"]
    kind = film.get('script_type')
    if kind is not None and kind not in types():
        out.append(f"script_type: {kind!r} is not in the library ({', '.join(types())})")
        kind = None
    L = languages()[lang]
    if lang != 'tk':                                                     # Time Keeper style's own words: HOUSE_WORDS
        for ln in lines:
            for w in L.get('avoid', []):
                if _has(w, _spoken(ln)):
                    out.append(f"{ln['id']}: «{w}» does not belong in {L['name']} (brand/script_library.yaml, its rules)")
    if lang == 'tk':                                                     # Kuwaiti a light touch, not the base
        middle = [ln for ln in lines if not (ln.get('cold_open') or ln.get('closing'))]
        marked = [ln['id'] for ln in middle if any(_has(w, _spoken(ln)) for w in KUWAITI)]
        if len(marked) > TK_KUWAITI_LINES:
            out.append(f"Kuwaiti in {len(marked)} lines ({', '.join(marked)}): in {L['name']} it is a light touch, "
                       f"at most {TK_KUWAITI_LINES} lines besides the hook and the closing; or set language: kuwaiti")
    if kind:
        T = types()[kind]
        if lang not in T['languages']:
            out.append(f"{T['name']} is usually written in {' or '.join(languages()[k]['name'] for k in T['languages'])}, "
                       f"not {L['name']} (keep it only if you chose it)")
        lo, hi = T['seconds']
        est = estimate(film)['seconds']
        if est > hi * 1.1 or est < lo * 0.8:
            out.append(f"about {est:.0f} s of voice; {T['name']} runs {lo}–{hi} s: cut a fact, never a bridge" if est > hi
                       else f"about {est:.0f} s of voice; {T['name']} runs {lo}–{hi} s")
    return out


def card(kind: str, lang: str | None = None) -> str:
    """A type as the owner sees it: its job, length, acts with a skeleton line each, and its language's example."""
    T, lang = types()[kind], lang or (types()[kind]['languages'][0])
    L = languages()[lang]
    rows = [f"{T['name']} · {T['seconds'][0]}–{T['seconds'][1]} ث · {L['name']}", T['job'], '']
    rows += [f"{i}. {a['name']} ({round(a['share'] * 100)}%): {a['example']}" for i, a in enumerate(T['acts'], 1)]
    rows += ['', f"مثال {L['name']}:", f"  {L['example']['hook']}", f"  {L['example']['line']}", f"  {L['example']['close']}"]
    return '\n'.join(rows)
