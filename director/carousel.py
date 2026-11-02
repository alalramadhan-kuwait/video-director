"""A topic as a carousel instead of (or beside) a Reel: the owner's tk-topic-carousel kit inside the reel-master flow.

The owner, 2 Nov 2026: «have the option to generate the topic as a carousel instead of video if required… integrated
into dashboard with availability to save along with caption».

A carousel is a spec (`carousels/<name>/spec.json`, beside its images): a TK cover with two headline lines, then 4–5
written slides, one idea each, each with a large cut-out image, plus the post caption (`caption.txt`).
`check()` holds it to the kit's rules and to the script's language; `render()` runs tools/carousel/carousel.mjs."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from . import scripts

ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / 'tools/carousel/carousel.mjs'
LAYOUTS = ('topImage', 'rightBleed', 'bottomImage', 'leftBleed', 'bigCorner')
COVER_MAX = 73                     # top + bottom headline characters (the TK post template)
SLIDES = (4, 5)
BODY_WORDS = (25, 32)
TITLE_WORDS = (2, 4)


def words(html: str) -> list[str]:
    return [w for w in re.sub(r'<[^>]+>', ' ', html or '').split() if re.search(r'\w', w)]


def layouts(spec: dict) -> list[str]:
    """Each slide's layout as the renderer will draw it (its own `layout`, else the rotation)."""
    return [s.get('layout') or LAYOUTS[i % len(LAYOUTS)] for i, s in enumerate(spec.get('slides', []))]


def check(spec: dict, base: Path | None = None, language: str = 'tk') -> list[str]:
    """What the carousel breaks of the kit's rules. Empty when it keeps them."""
    out, cover, slides = [], spec.get('cover') or {}, spec.get('slides') or []
    head = (cover.get('top') or '') + (cover.get('bottom') or '')
    if not cover.get('top'): out.append('cover: the top headline line is required')
    if len(head) > COVER_MAX: out.append(f'cover: {len(head)} characters in the headline; at most {COVER_MAX}')
    if not SLIDES[0] <= len(slides) <= SLIDES[1]: out.append(f'{len(slides)} written slides; the carousel has {SLIDES[0]}–{SLIDES[1]}')
    seq = layouts(spec)
    for i, s in enumerate(slides, 1):
        n = len(words(s.get('body')))
        if not BODY_WORDS[0] <= n <= BODY_WORDS[1]:
            out.append(f'slide {i}: {n} words; a slide is {BODY_WORDS[0]}–{BODY_WORDS[1]} (the fact and one line of why)')
        t = len(words(s.get('title')))
        if not TITLE_WORDS[0] <= t <= TITLE_WORDS[1]:
            out.append(f'slide {i}: a title of {t} words; {TITLE_WORDS[0]}–{TITLE_WORDS[1]}')
        if s.get('layout') and s['layout'] not in LAYOUTS: out.append(f"slide {i}: layout {s['layout']!r} is not one of {', '.join(LAYOUTS)}")
        if i > 1 and seq[i - 1] == seq[i - 2]: out.append(f'slide {i}: the same layout as slide {i - 1} ({seq[i - 1]}); vary it')
        if not s.get('image'): out.append(f'slide {i}: no image (one large cut-out per slide)')
        if s.get('watch') and seq[i - 1] in ('rightBleed', 'leftBleed', 'bigCorner'):
            out.append(f'slide {i}: a watch is shown whole; {seq[i - 1]} cuts it off the slide (topImage or bottomImage)')
    if base is not None:
        for what, p in [('cover', cover.get('image'))] + [(f'slide {i}', s.get('image')) for i, s in enumerate(slides, 1)]:
            if p and not (Path(p) if Path(p).is_absolute() else base / p).is_file(): out.append(f'{what}: image {p} is missing')
    lines = [{'id': 'cover', 'text': head}] + [{'id': f'slide {i}', 'text': f"{s.get('title', '')} {re.sub(r'<[^>]+>', ' ', s.get('body', ''))}"}
                                             for i, s in enumerate(slides, 1)]
    out += [m for m in scripts.check({'lines': lines, 'language': language}) if 'belong' in m]   # the language's words
    return out


def render(spec_path: Path, out: Path) -> list[Path]:
    """The PNGs, 01_cover then the slides, as the renderer printed them."""
    r = subprocess.run(['node', str(RENDERER), str(spec_path), str(out)], capture_output=True, text=True, check=True)
    return [Path(l[5:]) for l in r.stdout.splitlines() if l.startswith('FILE:')]


def load(folder: Path) -> tuple[dict, str]:
    folder = Path(folder)
    spec = json.loads((folder / 'spec.json').read_text(encoding='utf-8'))
    cap = folder / 'caption.txt'
    return spec, cap.read_text(encoding='utf-8').strip() if cap.is_file() else ''
