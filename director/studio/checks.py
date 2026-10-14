"""Script checks run on every script version (automatic, explainable, never edit the text).

  SPELLING            a word one or two letters away from a known word (research terms, the brand glossary, every word
                      of earlier versions of this script) but not equal to it: «فيلسدروف» next to «فيلسدورف»
  REPEATED_WORD       the same word twice in a row
  CLAIM_UNSUPPORTED   a clause that makes a claim the research marks 'avoid'. Two layers: the claim's exact phrases, and its
                      RULE (all of several word groups in one clause, e.g. first/preceded + watch + water-resistant),
                      so a paraphrase is caught too. Attribution («يقولون», «قدّمتها رولكس») or a denial («لم تكن») only
                      counts when it comes BEFORE the claim in the SAME clause. Heuristic: it narrows what a person reads;
                      it does not replace reading.
  (Spelling) covers names, terms and long words the owner already approved; it is not a full Arabic spell checker.
  LATIN_IN_NARRATION  Latin letters in a narration line (captions are Arabic; the final voice gets Latin names from the
                      pronunciation library, not from the script)
  DIGITS              digits in narration (Time Keeper narration says numbers as words; captions may show digits)
  LONG_LINE           more than 30 words: hard to time and to caption
  NAME_TO_CHECK       a foreign name or term from the research list: listen to it in the voice step
"""
from __future__ import annotations
import difflib, re

from ..vendor.arabic import strip

WORD = re.compile(r'[ء-يً-ْٰـ]+|[A-Za-z][A-Za-z\'’-]*|\d+')
PROCLITIC = re.compile(r'^(و|ف)?(ب|ل|ك)?(ال)?')
GLOSSARY = ['ساعة', 'ساعات', 'مقاومة', 'للماء', 'الماء', 'التاج', 'اللولبي', 'الإطار', 'الغطاء', 'الخلفي', 'العلبة',
            'براءة', 'اختراع', 'سويسرية', 'سويسرا', 'رولكس', 'أويستر', 'المحارة', 'معصم', 'معصمها', 'الحركة']


def words(text: str) -> list[str]:
    """The words of a line as the user sees them (tokens a person can tap)."""
    return [m.group() for m in WORD.finditer(text)]


def bare(w: str) -> str:
    w = strip(w)
    return re.sub('[أإآ]', 'ا', w)


def stem(w: str) -> str:
    b = bare(w)
    m = PROCLITIC.match(b)
    s = b[len(m.group(0)):] if m and len(b) - len(m.group(0)) >= 3 else b
    return s


def _dl(a: str, b: str) -> int:
    """Damerau-Levenshtein distance (a swap of two neighbouring letters counts as one)."""
    d = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1): d[i][0] = i
    for j in range(len(b) + 1): d[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            c = 0 if a[i - 1] == b[j - 1] else 1
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + c)
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[len(a)][len(b)]


def vocabulary(research: dict | None, earlier: list[dict]) -> dict:
    """known stem -> where it comes from: research names/terms, the glossary, and long words of APPROVED versions only
    (a typo in a draft or a rejected version must not become 'known' and hide itself in the next version)."""
    vocab = {}
    for g in GLOSSARY: vocab.setdefault(stem(g), 'glossary')
    for t in (research or {}).get('terms', []):
        for w in t['ar'].split(): vocab.setdefault(stem(w), f"research term «{t['ar']}»")
    for v in earlier:
        if v.get('status') != 'approved': continue
        for ln in v['lines']:
            for w in words(ln['text']):
                if re.match('[ء-ي]', w) and len(stem(w)) >= 6: vocab.setdefault(stem(w), f"approved v{v['v']}")
    return vocab


CLAUSE = re.compile(r'[،,.؛;!?؟…]+|\s(?:لكن|لكنّ|بل|والحقيقة|الحقيقة)\s')   # not ':' — «يقولون: …» introduces the attributed words


def _claim_hits(text: str, claim: dict) -> list[str]:
    """Clauses of `text` that make the claim without being attributed or denied before it."""
    rule = claim.get('rule')
    hits = []
    for clause in CLAUSE.split(' ' + text + ' '):
        flat = bare(clause)
        toks = [stem(w) for w in words(clause)]
        found = [p for p in claim.get('patterns', []) if bare(p) in flat]
        pos, inverted = None, False
        if found:
            pos = flat.index(bare(found[0]))
        elif rule:
            idx = []
            for group in rule['all_of']:
                g = [stem(x) for x in group]
                at = next((i for i, t in enumerate(toks) if any(t.startswith(x) or x in t for x in g)), None)
                if at is None: break
                idx.append(at)
            else:
                ws = [bare(w) for w in words(clause)]
                i0 = idx[0]                                     # the 'first / preceded' word
                if ws[i0].endswith('اول') and i0 + 1 < len(ws) and ws[i0 + 1] == 'ما':
                    continue                                    # «أول ما يدخل الماء…» = 'the first thing that…', not a claim
                pos = flat.index(bare(words(clause)[min(idx)])) if words(clause) else 0
                inv = [stem(x) for x in rule.get('negation_affirms', [])]   # «لم يسبقها أحد» = she was first
                inverted = any(toks[i0].startswith(x) or x in toks[i0] for x in inv)
                neg = {bare(n) for n in rule.get('negation', [])}
                negated = any(ws[j] in neg for j in range(max(0, i0 - 2), i0))     # the negation belongs to that verb
                if inverted and not negated and re.search(r'(ها|ه|هم|هما)$', toks[i0]):
                    continue                                    # «سبقتها ساعات…»: something came BEFORE it — the opposite claim
        if pos is None: continue
        before = flat[:pos]
        if any(re.search(r'(^|\s)[وفبل]?' + re.escape(bare(a)), before) for a in claim.get('allowed_with', [])):
            continue                                            # a whole word: «ثقيلة» does not contain the attribution «قيل»
        if not inverted and any(re.search(r'(^|\s)' + bare(n) + r'(\s|$)', before) for n in (rule or {}).get('negation', [])):
            continue
        hits.append(clause.strip())
    return hits


def check_version(lines: list[dict], research: dict | None, earlier: list[dict]) -> list[dict]:
    vocab = vocabulary(research, earlier)
    known = set(vocab)
    names = {stem(w): t['term'] for t in (research or {}).get('terms', []) for w in t['ar'].split() if len(stem(w)) >= 3}
    avoid = [c for c in (research or {}).get('claims', []) if c.get('status') == 'avoid']
    out = []
    for ln in lines:
        lid, text = ln['id'], ln['text']
        ws = words(text)
        for i, w in enumerate(ws):
            if re.match('[A-Za-z]', w):
                out.append(_f('LATIN_IN_NARRATION', 'minor', lid, i, w, 'Latin letters in narration: write the Arabic form; '
                              'the final voice gets the Latin spelling from the pronunciation library'))
                continue
            if w.isdigit():
                out.append(_f('DIGITS', 'minor', lid, i, w, 'Time Keeper narration says numbers as words'))
                continue
            s = stem(w)
            if i and bare(ws[i - 1]) == bare(w):
                out.append(_f('REPEATED_WORD', 'major', lid, i, w, f'«{w}» twice in a row'))
            if s in names:
                out.append(_f('NAME_TO_CHECK', 'info', lid, i, w, f'foreign name or term ({names[s]}): listen to it in the voice step'))
            if len(s) >= 5 and s not in known:
                near = [k for k in known if abs(len(k) - len(s)) <= 2 and len(k) >= 5 and _dl(s, k) <= (1 if len(s) < 8 else 2)]
                near = [k for k in near if not (k.startswith(s) or s.startswith(k))]          # inflections are not typos
                if near:
                    k = min(near, key=lambda k: _dl(s, k))
                    out.append(_f('SPELLING', 'major', lid, i, w, f'«{w}» looks like a misspelling of «{k}» ({vocab[k]})',
                                  suggestion=_respell(w, s, k)))
        if len(ws) > 30:
            out.append(_f('LONG_LINE', 'minor', lid, None, None, f'{len(ws)} words: split the line'))
        for c in avoid:
            for clause in _claim_hits(text, c):
                out.append(_f('CLAIM_UNSUPPORTED', 'critical', lid, None, clause,
                              f'«{clause}» states a claim the research marks avoid ({c["id"]}): {c["why"]}'))
    return out


def _respell(w: str, s: str, k: str) -> str:
    """The word with its stem replaced by the known stem, keeping the proclitics as written."""
    b = bare(w)
    pre = b[:len(b) - len(s)]
    return pre + k


def _f(code, severity, line, wi, word, detail, suggestion=None):
    return {'code': code, 'severity': severity, 'line': line, 'wi': wi, 'word': word, 'detail': detail,
            **({'suggestion': suggestion} if suggestion else {})}


def word_diff(a: list[dict], b: list[dict]) -> list[dict]:
    """Word-level differences between two versions, line by line (added/removed lines included)."""
    A, Bm = {l['id']: l['text'] for l in a}, {l['id']: l['text'] for l in b}
    out = []
    for lid in list(dict.fromkeys([*A, *Bm])):
        if lid not in A: out.append({'line': lid, 'op': 'line_added', 'new': Bm[lid]}); continue
        if lid not in Bm: out.append({'line': lid, 'op': 'line_removed', 'old': A[lid]}); continue
        wa, wb = A[lid].split(), Bm[lid].split()
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, wa, wb, autojunk=False).get_opcodes():
            if tag != 'equal':
                out.append({'line': lid, 'op': tag, 'at': i1, 'old': ' '.join(wa[i1:i2]), 'new': ' '.join(wb[j1:j2])})
    return out
