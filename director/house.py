"""The house rules gate: every owner correction a machine can check (brand/house_rules.yaml), applied to any text
before it reaches the owner, and before a paid voice take. `check()` lists what breaks a rule; `fix()` rewrites what
can be rewritten safely (the `fix` list and the names)."""
from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / 'brand/house_rules.yaml'
HARAKAT = re.compile('[ً-ْٰـ]')


def rules(path: Path = RULES) -> dict:
    return yaml.safe_load(path.read_text(encoding='utf-8')) or {}


def plain(t: str) -> str:
    return HARAKAT.sub('', re.sub(r'<[^>]+>', ' ', t or ''))


def _word(w: str) -> re.Pattern:
    """A whole word, with the Arabic one-letter prefixes (و ف ب ل ك ال) allowed before it."""
    return re.compile(r'(?<![\w])(?:[وفبلك]?(?:ال)?)' + re.escape(w) + r'(?![\w])')


def fix(text: str, R: dict | None = None) -> str:
    R = R or rules()
    out = text or ''
    for f in R.get('fix', []):
        out = re.sub(re.escape(f['from']), f['to'], out)
    for a, b in sorted((R.get('names') or {}).items(), key=lambda kv: -len(kv[0])):
        out = out.replace(a, b)
    return out


def check(text: str, where: str = '', R: dict | None = None, caption: bool = False, ok: list | None = None) -> list[str]:
    R = R or rules()
    t, out, ok = plain(text), [], set(ok or [])
    for f in R.get('fix', []):
        if f['from'] in t: out.append(f"{where}: «{f['from']}» → «{f['to']}» ({f.get('why', '')})")
    for a, b in (R.get('names') or {}).items():
        if a in t: out.append(f"{where}: the name «{a}» is written «{b}»")
    for f in R.get('flag', []):
        if f.get('word') in ok: continue
        rx = re.compile(f['pattern']) if f.get('pattern') else _word(f['word'])
        m = rx.search(t)
        if m: out.append(f"{where}: «{m.group(0).strip()}»: {f['hint']}")
    if caption:
        c = R.get('caption') or {}
        if c.get('no_hashtags') and re.search(r'(^|\s)#\S', text or ''): out.append(f'{where}: no hashtags in a caption')
        for line in (text or '').splitlines():
            if any(line.strip().startswith(s) for s in c.get('no_lines_starting', [])):
                out.append(f'{where}: no sources or credits in a caption («{line.strip()[:30]}…»)')
        raw = (text or '').strip()
        if c.get('max_chars') and len(raw) > c['max_chars']:
            out.append(f"{where}: {len(raw)} characters; a caption is at most {c['max_chars']}: one key fact, short details, one question")
        lines = raw.splitlines()
        if c.get('blank_line_between_paragraphs') and any(a.strip() and b.strip() for a, b in zip(lines, lines[1:])):
            out.append(f'{where}: leave a blank line between paragraphs')
        listy = [l for l in lines if re.match(r'^[^:\n]{2,40}:\s', l.strip())]
        if c.get('max_list_lines') is not None and len(listy) > c['max_list_lines']:
            out.append(f'{where}: {len(listy)} «X: Y» lines: the slides explain, the caption does not list them')
        for w in c.get('formal', []):
            if w in (text or '') or w in t: out.append(f'{where}: «{w}» is formal; write it as Time Keeper talks')
    return out


def check_lines(lines: list, R: dict | None = None, ok: list | None = None) -> list[str]:
    """A film's script lines (their text and what the voice says); `ok`: flagged words Claude confirmed are right here."""
    R = R or rules()
    out = []
    for i, ln in enumerate(lines, 1):
        for key in ('text', 'say'):
            if ln.get(key): out += check(ln[key], f'line {i}' + ('' if key == 'text' else ' (say)'), R, ok=ok)
    return list(dict.fromkeys(out))


def check_carousel(spec: dict, caption: str = '', R: dict | None = None) -> list[str]:
    R = R or rules()
    c = spec.get('cover') or {}
    out = check(f"{c.get('top', '')} {c.get('bottom', '')}", 'cover', R)
    for i, s in enumerate(spec.get('slides') or [], 1):
        out += check(' '.join(str(s.get(k) or '') for k in ('title', 'body', 'ask')) + ' ' + ' '.join(str(c.get('title') or '') for c in s.get('cards') or []), f'slide {i}', R)
    if caption: out += check(caption, 'caption', R, caption=True)
    return out
