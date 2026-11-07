"""The owner's Kuwaiti word book (brand/kuwaiti-words.json), applied before any recording.

apply(text)      the voice's text with every 'auto' word written the way he chose (whole words; a joined و ب ل ف ك,
                 or two of them, stays). Idempotent: a word already carrying his marks is left alone.
check(lines)     what to show him on the script card before paying for a take:
                 'ask' words (wording he changed before) and NEW risky words: a word with ق or ج (the letters the
                 Kuwaiti way changes) that is neither in the word book nor in brand/kuwaiti-heard.json (approved by ear).
The feminine «ـها» always gets its sukun (kuwaiti-voice.md rules 13–15, his ten-spelling test): داخلها → داخلْها.
A film may list words it has cleared in `kw_ok:`; record_flow stops on anything else unless --anyway."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LETTER = r'ء-يٮ-ۓ'
MARKS = r'ً-ٰٟ'
PRE = '[وبلفك]{0,2}'


def book() -> list:
    f = ROOT / 'brand' / 'kuwaiti-words.json'
    return json.loads(f.read_text(encoding='utf-8')).get('words', []) if f.is_file() else []


def heard() -> set:
    f = ROOT / 'brand' / 'kuwaiti-heard.json'
    return set(json.loads(f.read_text(encoding='utf-8')).get('words', [])) if f.is_file() else set()


def bare(w: str) -> str:
    return re.sub(f'[{MARKS}ـ]', '', w)


def _rx(word: str) -> re.Pattern:
    return re.compile(rf'(?<![{LETTER}{MARKS}])({PRE}){re.escape(word)}(?![{LETTER}{MARKS}])')


HA = re.compile(rf'(?<![{LETTER}{MARKS}])([{LETTER}]{{2,}})([\u0628-\u0647\u0629\u062a])(ها)(?![{LETTER}{MARKS}])')   # not after a long vowel (معاها، فيها)


def apply(text: str, words: list | None = None) -> str:
    for e in sorted([e for e in (book() if words is None else words) if e.get('kind') == 'auto'], key=lambda e: -len(e['word'])):
        text = _rx(e['word']).sub(lambda m, s=e['say']: m.group(1) + s, text)
    return HA.sub(lambda m: m.group(1) + m.group(2) + '\u0652' + m.group(3), text)   # the sukun before «ـها»


def tokens(text: str) -> list:
    return re.findall(rf'[{LETTER}{MARKS}]+', text)


def risky(w: str) -> bool:
    b = bare(w)
    return bool(re.search('[قج]', b))


def check(lines: list, ok: list | None = None, words: list | None = None, known: set | None = None) -> list:
    """[{line, word, kind: 'ask'|'new', say?, note?}], one per (line, word)."""
    words = book() if words is None else words
    known = heard() if known is None else known
    ok = {bare(w) for w in (ok or [])}
    booked = {bare(e['word']) for e in words} | {bare(e['say']) for e in words}
    out, seen = [], set()
    for i, ln in enumerate(lines):
        say = ln.get('say') or ln.get('text') or ''
        for e in words:
            if e.get('kind') == 'ask' and _rx(e['word']).search(bare(say)) and bare(e['word']) not in ok:
                k = (i, e['word'])
                if k not in seen: seen.add(k); out.append({'line': i, 'word': e['word'], 'kind': 'ask', 'say': e['say'], 'note': e.get('note', '')})
        for w in tokens(apply(say, words)):
            b = re.sub(f'^{PRE}', '', bare(w))
            if not risky(w) or bare(w) in known or b in known or bare(w) in booked or b in booked or bare(w) in ok or b in ok: continue
            if w != bare(w): continue                  # the script already marks how it is said
            k = (i, b)
            if k not in seen: seen.add(k); out.append({'line': i, 'word': w, 'kind': 'new'})
    return out
