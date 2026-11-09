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


END = re.compile(r'[.!؟?…]|\n')
LATIN = re.compile(r'[A-Za-z][A-Za-z\-\.]{2,}')


def feed_window(text: str, n: int = 125) -> tuple[str, bool]:
    """What the feed shows before «… more», and whether its first sentence ends inside it."""
    raw = (text or '').strip()
    m = END.search(raw)
    return raw[:n], bool(m) and m.start() < n


def spoken_seconds(line: str, R: dict | None = None) -> float:
    """How long Faisal takes to say a line, estimated from our own takes (emotion tags and markup left out)."""
    R = R or rules()
    t = re.sub(r'\[[^\]]*\]', '', plain(line)).strip()
    return round(len(t) / float((R.get('voice') or {}).get('chars_per_second', 12.4)), 1)


def check(text: str, where: str = '', R: dict | None = None, caption: bool = False, ok: list | None = None,
          search: list | None = None) -> list[str]:
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
        if c.get('feed_window') and raw:
            win, whole = feed_window(raw, c['feed_window'])
            if not whole:
                out.append(f"{where}: the first sentence runs past the {c['feed_window']} characters the feed shows before «… more»; end the key fact inside it")
            if not (re.search(r'\d', win) or LATIN.search(win) or '«' in win):
                out.append(f"{where}: the first {c['feed_window']} characters name nothing concrete; put the watch, the brand or the number there")
        if c.get('needs_latin_name') and raw and not LATIN.search(raw):
            out.append(f'{where}: no brand or model in English letters; Instagram search reads the caption, so write it as people type it (e.g. «Rolex Day-Date»)')
        low = raw.lower()
        for term in search or []:
            if str(term).strip() and str(term).strip().lower() not in low:
                out.append(f'{where}: the search phrase «{term}» is missing; put it in a sentence')
    return out


def check_lines(lines: list, R: dict | None = None, ok: list | None = None) -> list[str]:
    """A film's script lines (their text and what the voice says); `ok`: flagged words Claude confirmed are right here,
    and `hook_time` / `line_time` when Claude confirmed a long hook or line is right for this film."""
    R = R or rules()
    out, ok, V = [], set(ok or []), R.get('voice') or {}
    for i, ln in enumerate(lines, 1):
        for key in ('text', 'say'):
            if ln.get(key): out += check(ln[key], f'line {i}' + ('' if key == 'text' else ' (say)'), R, ok=ok)
        spoken = ln.get('say') or ln.get('text') or ''
        if not spoken or not V: continue
        sec = spoken_seconds(spoken, R)
        if i == 1 and V.get('hook_max_s') and sec > V['hook_max_s'] and 'hook_time' not in ok:
            out.append(f"line 1: the hook takes about {sec} s to say; keep it under {V['hook_max_s']} s (cut it to the claim)")
        shots = ln.get('shots')
        if V.get('line_max_s') and sec > V['line_max_s'] and not (isinstance(shots, list) and len(shots) > 1) and 'line_time' not in ok:
            out.append(f"line {i}: about {sec} s on one picture; split the line, or plan two shots for it (`shots:`)")
    return list(dict.fromkeys(out))


def check_carousel(spec: dict, caption: str = '', R: dict | None = None) -> list[str]:
    R = R or rules()
    c = spec.get('cover') or {}
    out = check(f"{c.get('top', '')} {c.get('bottom', '')}", 'cover', R)
    for i, s in enumerate(spec.get('slides') or [], 1):
        out += check(' '.join(str(s.get(k) or '') for k in ('title', 'body', 'ask')) + ' ' + ' '.join(str(c.get('title') or '') for c in s.get('cards') or []), f'slide {i}', R)
    if caption: out += check(caption, 'caption', R, caption=True, search=spec.get('search'))
    return out
