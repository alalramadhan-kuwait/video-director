"""The brand config (brand/<id>.json): one place for fonts, captions, narration, music, logo and export.

Every step asks this module instead of keeping its own copy, so a change in the file reaches the whole film.
"""
from __future__ import annotations
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = 'timekeeper'
ALIAS = {'timekeeper': 'timekeeper', 'time-keeper': 'timekeeper', 'tk': 'timekeeper'}


def load(brand: str | None = None) -> dict:
    """The brand's config, or {} for a brand that has none (it then keeps the renderer's own defaults)."""
    f = ROOT / 'brand' / f'{ALIAS.get(brand or DEFAULT, brand)}.json'
    return json.loads(f.read_text(encoding='utf-8')) if f.is_file() else {}


def style(base: dict, brand: str | None = None) -> dict:
    """The renderer's storyboard style with the brand's fonts and captions applied."""
    b = load(brand)
    if not b: return base
    st = json.loads(json.dumps(base))
    fonts, cap = b.get('fonts', {}), b.get('captions', {})
    st.setdefault('banner', {})
    if fonts.get('banner'): st['banner']['font'] = fonts['banner']
    st['caption'] = {**st.get('caption', {}), **({'font': fonts['caption']} if fonts.get('caption') else {}),
                     **{k: cap[k] for k in ('bg', 'ink') if cap.get(k)}}
    return st


def caption_size(brand: str | None = None):
    return load(brand).get('captions', {}).get('size')


def music(brand: str | None = None) -> tuple[Path, float] | None:
    """The first library track that has its commercial licence record beside it (track.licence.json with a
    'licence' and a 'source'), and its gain. No such track: no music (never an unlicensed one)."""
    m = load(brand).get('music') or {}
    lib = ROOT / m.get('library', 'brand/music')
    if not lib.is_dir(): return None
    for f in sorted(lib.iterdir()):
        if f.suffix.lower() not in ('.mp3', '.m4a', '.wav', '.aac', '.ogg'): continue
        rec = f.with_suffix('.licence.json')
        try:
            r = json.loads(rec.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if r.get('licence') and r.get('source') and r.get('commercial_use', True):
            return f, float(m.get('gain_db', -22))
    return None


def lexicon(brand: str | None = None) -> dict:
    p = (load(brand).get('narration') or {}).get('pronunciation')
    if not p or not (ROOT / p).is_file(): return {}
    return {k: v for k, v in json.loads((ROOT / p).read_text(encoding='utf-8')).items() if not k.startswith('_')}


def spoken(text: str, brand: str | None = None, lex: dict | None = None) -> str:
    """The text the voice is given: watch names replaced by how they are said (longest names first, whole words)."""
    lex = lexicon(brand) if lex is None else lex
    for k in sorted(lex, key=len, reverse=True):
        text = re.sub(r'(?<![\w؀-ۿ])' + re.escape(k) + r'(?![\w؀-ۿ])', lex[k], text)
    return text
