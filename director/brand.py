"""The brand config (brand/<id>.json): one place for fonts, captions, narration, music, logo and export.

Every step asks this module instead of keeping its own copy, so a change in the file reaches the whole film.
"""
from __future__ import annotations
import hashlib, json, os, re, time, urllib.parse, urllib.request
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


AUDIO = ('.mp3', '.m4a', '.wav', '.aac', '.ogg')


def _own(lib: Path) -> list[dict]:
    """The owner's own tracks in the library folder, each with its licence record beside it (track.licence.json with a
    'licence' and a 'source', not marked non-commercial). A track without one is never used."""
    out = []
    for f in sorted(lib.iterdir()) if lib.is_dir() else ():
        if f.suffix.lower() not in AUDIO: continue
        try:
            r = json.loads(f.with_suffix('.licence.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if r.get('licence') and r.get('source') and r.get('commercial_use', True):
            out.append({'title': r.get('title') or f.stem, 'path': f, 'licence': r['licence'], 'source': r['source'],
                        'credit': r.get('attribution') or '', 'seconds': r.get('seconds'), 'feel': r.get('feel', []), 'own': True})
    return out


def catalog(brand: str | None = None) -> list[dict]:
    """Every track the brand may use: its own licensed tracks first, then the listed catalogues (brand/music/*.json:
    the whole list of a free commercial library, the audio fetched only when a film uses it)."""
    m = load(brand).get('music') or {}
    out = _own(ROOT / m.get('library', 'brand/music'))
    for c in m.get('catalogs', []):
        try:
            d = json.loads((ROOT / c).read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if not (d.get('licence') and d.get('commercial_use')): continue
        for t in d['tracks']:
            out.append({**t, 'licence': d['licence'], 'source': d['download'].format(file=urllib.parse.quote(t['file'])),
                        'credit': d['attribution'].format(title=t['title']), 'own': False})
    return out


def ranked(brand: str | None = None, seconds: float | None = None, mood: list[str] | None = None) -> list[dict]:
    """Catalogue tracks that fit the brand, best first: none of its 'avoid' feels or words and no faster than its
    'max_bpm'; ranked by its 'prefer' feels (in order), its instruments, and being long enough not to loop."""
    m = load(brand).get('music') or {}
    prefer, avoid = mood or m.get('prefer', []), set(m.get('avoid', []))
    inst = [i.lower() for i in m.get('instruments', [])]
    words = [w.lower() for w in m.get('avoid_words', [])]
    def fits(t):
        hay = f"{t['title']} {t.get('instruments', '')} {t.get('about', '')}".lower()
        return not (avoid & set(t.get('feel') or []) or any(w in hay for w in words) or (t.get('bpm') or 0) > m.get('max_bpm', 999))
    def score(t):
        s = sum(len(prefer) - prefer.index(f) for f in t.get('feel') or [] if f in prefer)
        s += sum(1 for i in inst if i in (t.get('instruments') or '').lower())
        if seconds and (t.get('seconds') or 0) < seconds: s -= 4          # too short: it would loop
        return s
    return sorted((t for t in catalog(brand) if not t['own'] and fits(t) and score(t) > 0), key=lambda t: (-score(t), t['title']))


def choose(brand: str | None = None, seconds: float | None = None, seed: str = '', title: str | None = None,
           mood: list[str] | None = None) -> dict | None:
    """The track for a film. A named title wins; then the owner's own track if there is one; else one of the ten best
    catalogue tracks, picked by the film's `seed`, so films differ but the same film always gets the same track."""
    if title:
        return next((t for t in catalog(brand) if t['title'].lower() == title.lower()), None)
    own = [t for t in catalog(brand) if t['own']]
    if own: return own[0]
    ok = ranked(brand, seconds, mood)[:10]
    if not ok: return None
    return ok[int(hashlib.sha256(seed.encode()).hexdigest(), 16) % len(ok)]


def fetch(t: dict) -> Path | None:
    """The track's audio on disk: an own track as it is; a catalogue track downloaded once into the cache with its licence
    record beside it (source, licence, credit, date, sha256). No network or a bad download: None (the film has no music)."""
    if t.get('path'): return Path(t['path'])
    cache = Path(os.environ.get('VD_MUSIC_CACHE') or Path.home() / '.cache' / 'video-director' / 'music')
    f = cache / t['file']
    if f.is_file() and f.with_suffix('.licence.json').is_file(): return f
    try:
        with urllib.request.urlopen(urllib.request.Request(t['source'], headers={'User-Agent': 'VideoDirector/0.3'}), timeout=60) as r:
            data = r.read(40 * 1024 * 1024)
    except Exception:
        return None
    if len(data) < 50_000 or not (data[:3] == b'ID3' or data[:2] in (b'\xff\xfb', b'\xff\xf3', b'\xff\xf2')):
        return None                                                       # not an mp3 (an error page): never used
    cache.mkdir(parents=True, exist_ok=True)
    f.write_bytes(data)
    f.with_suffix('.licence.json').write_text(json.dumps({
        'title': t['title'], 'licence': t['licence'], 'source': t['source'], 'commercial_use': True, 'attribution': t['credit'],
        'downloaded': time.strftime('%Y-%m-%d'), 'sha256': hashlib.sha256(data).hexdigest()}, ensure_ascii=False, indent=1), encoding='utf-8')
    return f


def music(brand: str | None = None, seconds: float | None = None, seed: str = '', title: str | None = None) -> dict | None:
    """The film's music bed: {file, gain, title, licence, source, credit}, or None (no licensed track, or offline)."""
    t = choose(brand, seconds, seed, title)
    f = t and fetch(t)
    if not f: return None
    return {'file': f, 'gain': float((load(brand).get('music') or {}).get('gain_db', -22)), 'title': t['title'],
            'licence': t['licence'], 'source': t['source'], 'credit': t['credit']}


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
