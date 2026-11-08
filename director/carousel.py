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
FULL = 'full'                        # the photo is the slide, faded into its paper (tools/carousel/full_photo.py)
COVER_MAX = 73                     # top + bottom headline characters (the TK post template)
SLIDES = (4, 5)
BODY_WORDS = (12, 32)                # as little as the idea needs (the owner: «قلل النصوص»)
NEWS_WORDS = (3, 14)                 # a news carousel: one short fact under a big watch (the owner: «reduce the text»)
TITLE_WORDS = (2, 4)


def words(html: str) -> list[str]:
    return [w for w in re.sub(r'<[^>]+>', ' ', html or '').split() if re.search(r'\w', w)]


def layouts(spec: dict) -> list[str]:
    """Each slide's layout as the renderer will draw it (its own `layout`, else the rotation)."""
    return [s.get('layout') or LAYOUTS[i % len(LAYOUTS)] for i, s in enumerate(spec.get('slides', []))]


def cut_out(path: Path) -> bool:
    """True when a picture has real transparency: a background-removed cut-out."""
    try:
        from PIL import Image
        im = Image.open(path)
        if im.mode not in ('RGBA', 'LA', 'PA') and 'transparency' not in im.info: return False
        a = im.convert('RGBA').getchannel('A')
        return a.getextrema()[0] < 250
    except Exception:
        return False


def check(spec: dict, base: Path | None = None, language: str = 'tk') -> list[str]:
    """What the carousel breaks of the kit's rules. Empty when it keeps them."""
    out, cover, slides = [], spec.get('cover') or {}, spec.get('slides') or []
    head = (cover.get('top') or '') + (cover.get('bottom') or '')
    if cover.get('type') == 'chart':                                  # a ranking chart as the cover
        if not cover.get('title'): out.append('cover: the chart has a title')
        vals = [r.get('value') for r in cover.get('rows') or []]
        if not vals or any(not isinstance(v, (int, float)) for v in vals): out.append('cover: every chart row has a number `value`')
        elif vals != sorted(vals, reverse=True): out.append('cover: the chart rows run from the largest to the smallest')
    elif not cover.get('top'): out.append('cover: the top headline line is required')
    if len(head) > COVER_MAX: out.append(f'cover: {len(head)} characters in the headline; at most {COVER_MAX}')
    if not spec.get('news') and not SLIDES[0] <= len(slides) <= SLIDES[1]: out.append(f'{len(slides)} written slides; the carousel has {SLIDES[0]}–{SLIDES[1]}')
    last = slides[-1] if slides else {}
    if slides and not spec.get('news') and not (last.get('ask') or '').strip().endswith('؟'):
        out.append(f'slide {len(slides)}: the last slide ends on the reader\'s question, set large in `ask` '
                   '(the owner: «دائما سؤال القارئ يكون أكبر ويشد القارئ»)')
    for i, s in enumerate(slides[:-1], 1):
        if s.get('ask'): out.append(f'slide {i}: only the last slide asks the reader (`ask`)')
    seq = layouts(spec)
    for i, s in enumerate(slides, 1):
        if s.get('type') == 'price':                                  # the price-list style: one watch, its price
            if not s.get('image'): out.append(f'slide {i}: every card shows its watch')
            if not (s.get('brand') and s.get('model')): out.append(f'slide {i}: a price slide names the brand and the model')
            if not re.search(r'د\.ك', s.get('price') or ''): out.append(f'slide {i}: the price is in dinars («د.ك»), the official price in `price_note`')
            if not s.get('price_note'): out.append(f'slide {i}: `price_note` gives the official price it comes from')
            continue
        if s.get('type') == 'end':                                    # the TK green closing card
            if i != len(slides): out.append(f'slide {i}: the green end card is the last slide')
            if not s.get('title'): out.append(f'slide {i}: the end card has a title')
            continue
        if s.get('type') in ('cards', 'hero'):                       # the awards style: checked by its own shape
            if s['type'] == 'cards' and not 1 <= len(s.get('cards') or []) <= 6: out.append(f'slide {i}: 1–6 cards a slide')
            if any(not c.get('image') for c in s.get('cards') or []) or (s['type'] == 'hero' and not s.get('image')): out.append(f'slide {i}: every card shows its watch')
            continue
        n = len(words(s.get('body'))) + len(words(s.get('ask')))
        lo, hi = NEWS_WORDS if spec.get('news') else BODY_WORDS
        if not lo <= n <= hi:
            out.append(f'slide {i}: {n} words; a slide is {lo}–{hi} (as little as the idea needs)')
        t = len(words(s.get('title')))
        if not TITLE_WORDS[0] <= t <= TITLE_WORDS[1]:
            out.append(f'slide {i}: a title of {t} words; {TITLE_WORDS[0]}–{TITLE_WORDS[1]}')
        if s.get('layout') and s['layout'] not in LAYOUTS + (FULL,): out.append(f"slide {i}: layout {s['layout']!r} is not one of {', '.join(LAYOUTS + (FULL,))}")
        if s.get('paper') and str(s['paper']).lower() not in ('#fff', '#ffffff', 'white') and seq[i - 1] != FULL:
            out.append(f'slide {i}: a photo on its own ground sits as a box on the slide; make it the slide '
                       '(`"layout": "full"`, tools/carousel/full_photo.py) so the edge is seamless (the owner, 8 Nov 2026)')
        if i > 1 and seq[i - 1] == seq[i - 2] != FULL and not slides[i - 2].get('type'): out.append(f'slide {i}: the same layout as slide {i - 1} ({seq[i - 1]}); vary it')
        if not s.get('image'): out.append(f'slide {i}: no image (one large cut-out per slide)')
        if s.get('watch') and seq[i - 1] in ('rightBleed', 'leftBleed', 'bigCorner'):
            out.append(f'slide {i}: a watch is shown whole; {seq[i - 1]} cuts it off the slide (topImage or bottomImage)')
    if base is not None:
        for what, p in [('cover', cover.get('image'))] + [(f'slide {i}', s.get('image')) for i, s in enumerate(slides, 1)]:
            if p and not (Path(p) if Path(p).is_absolute() else base / p).is_file(): out.append(f'{what}: image {p} is missing')
        for i, s in enumerate(slides, 1):
            for c in s.get('cards') or []:
                q = c.get('image')
                if q and not (Path(q) if Path(q).is_absolute() else base / q).is_file(): out.append(f'slide {i}: image {q} is missing')
        for i, s in enumerate(slides, 1):
            p = s.get('image')
            f = p and (Path(p) if Path(p).is_absolute() else base / p)
            if s.get('watch') and f and f.is_file() and cut_out(f):
                out.append(f'slide {i}: the watch is a cut-out; keep the photo whole and set `paper` to its ground '
                           '(the owner: «you remove part of the watch»)')
    lines = [{'id': 'cover', 'text': head}] + [{'id': f'slide {i}', 'text': f"{s.get('title', '')} {re.sub(r'<[^>]+>', ' ', s.get('body', ''))} {s.get('ask', '')}"}
                                             for i, s in enumerate(slides, 1)]
    out += [m for m in scripts.check({'lines': lines, 'language': language}) if 'belong' in m]   # the language's words
    return out


def render(spec_path: Path, out: Path) -> list[Path]:
    """The PNGs, 01_cover then the slides, as the renderer printed them."""
    return render_report(spec_path, out)[0]


def render_report(spec_path: Path, out: Path) -> tuple[list[Path], list[str]]:
    """The PNGs and what the drawn slides break: text off the slide or into the picture, a cover line that shrank."""
    r = subprocess.run(['node', str(RENDERER), str(spec_path), str(out)], capture_output=True, text=True, check=True)
    lines = r.stdout.splitlines()
    return [Path(l[5:]) for l in lines if l.startswith('FILE:')], [l[5:] for l in lines if l.startswith('WARN:')]


def load(folder: Path) -> tuple[dict, str]:
    folder = Path(folder)
    spec = json.loads((folder / 'spec.json').read_text(encoding='utf-8'))
    cap = folder / 'caption.txt'
    return spec, cap.read_text(encoding='utf-8').strip() if cap.is_file() else ''
