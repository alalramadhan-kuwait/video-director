"""The voice gate: nothing is recorded while the script breaks a rule (the owner, 10 Nov 2026: «there should be a
gateway where if the rules are not applied it will not record»).

`tools/record_flow.py` is the only way a take is made. Before anything is paid for it runs every check here on the
script AND on the exact text the voice will be given, and stops when one fails. There is no flag that skips the
checks on the spoken text: they are the mistakes that cost a take (10 Nov 2026: a script written with English letters,
and «28,800» sent as digits came back «22,800»).

The house rules (brand/house_rules.yaml) and the owner's word book still run as before; this adds what they did not
see: the text as it is spoken, and the words on screen."""
from __future__ import annotations

import re

from director import house

LATIN = re.compile(r'[A-Za-z][A-Za-z\'’\-]*')
DIGITS = re.compile(r'\d')
ARTICLE = re.compile(r'(?<![\w؀-ۿ])(?:ال|بال|وال|فال|لل|كال)ـ?\s*[A-Za-z]')


def latin_ok(R: dict | None = None) -> set[str]:
    """English words the owner chose to have read as written (e.g. «Oyster», picked by ear on 4 Nov 2026)."""
    R = R or house.rules()
    return {w.lower() for w in ((R.get('voice') or {}).get('latin_ok') or [])}


def name_words(names) -> set[str]:
    """The Latin words of names the voice is meant to say in their own language (house style, rule 9e)."""
    return {w.lower() for n in (names or []) for w in LATIN.findall(str(n))}


def spoken_problems(spoken: list[str], R: dict | None = None, names=None) -> list[str]:
    """The text each line gives the voice, after the pronunciation book: what it must never contain. `names`: the
    names said in their own language (house style); their Latin words are meant to be there."""
    ok, out = latin_ok(R) | name_words(names), []
    for i, t in enumerate(spoken, 1):
        for m in DIGITS.finditer(t):
            num = re.search(r'[\d,.\-−+/٫]+', t[m.start():]).group(0)
            out.append(f'line {i} (voice): «{num}» goes to the voice as digits; write it in words in `say` (rule 9d)')
            break
        bad = [w for w in LATIN.findall(t) if w.lower() not in ok]
        if bad:
            out.append(f"line {i} (voice): {', '.join('«' + w + '»' for w in dict.fromkeys(bad))} in English letters; "
                       'write the English term in Arabic letters («مين سبرينغ»), or the owner clears it by ear (voice.latin_ok)')
        if ARTICLE.search(t):
            out.append(f'line {i} (voice): «ال» before an English word is lost when spoken; write the word in Arabic letters')
        if 'گ' in t:
            out.append(f'line {i} (voice): «گ» is never written; spell the word as a Kuwaiti reads it with ق or ك')
    return out


def screen_problems(lines: list[dict], R: dict | None = None, names=None) -> list[str]:
    """The script and the words on screen: an English technical term is written in Arabic letters (rule 16, the owner
    on 8 Nov 2026: «use the same English technical term, but write it in Arabic»). Digits are fine on screen. Only for
    a house-style film (rule 9e); a film made before it (`house_style: false`, Halter) writes names in Latin.
    `names`: the house names and the film's own (`names:`), which the script and the screen may keep in Latin."""
    ok, out = latin_ok(R) | name_words(names), []
    for i, ln in enumerate(lines, 1):
        for key in ('text', 'screen'):
            bad = [w for w in LATIN.findall(str(ln.get(key) or '')) if w.lower() not in ok]
            if bad:
                where = 'script' if key == 'text' else 'screen'
                out.append(f"line {i} ({where}): {', '.join('«' + w + '»' for w in dict.fromkeys(bad))} in English letters; "
                           'write the English term in Arabic letters (rule 16)')
        if 'گ' in str(ln.get('text') or '') + str(ln.get('screen') or ''):
            out.append(f'line {i}: «گ» is never written')
    return out


def check(lines: list[dict], spoken: list[str], R: dict | None = None, ok: list | None = None, names=None,
          screen: bool = True) -> list[str]:
    """Everything that stops a take: the house rules on the script, the words on screen (house style), and the
    spoken text."""
    R = R or house.rules()
    out = house.check_lines(lines, R, ok=ok) + (screen_problems(lines, R, names) if screen else []) + spoken_problems(spoken, R, names)
    return list(dict.fromkeys(out))
