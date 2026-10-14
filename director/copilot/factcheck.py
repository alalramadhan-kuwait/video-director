"""Script fact check for the Co-Pilot: three independent signals, merged so that no claim is approved silently.

  1. keyword   the existing research rule check (studio/checks.py): avoid-claims written as patterns. Precise when it
               fires, blind to paraphrases (UAT round 3: it missed «اخترعت رولكس الساعة المقاومة للماء»).
  2. assertion a language check of what a clause ASSERTS, independent of any project's rule: priority and invention
               claims (أول، اخترع، مخترع، رائد، بدأ عصر، الوحيد، أقدم، "nothing before X"), attributed or not, negated or
               not. An unattributed priority claim that shares its subject with an avoid-claim is a contradiction; any
               other unattributed priority claim is UNCERTAIN until a source backs it.
  3. AI        the fact checker (a separate AI call: mock or real) gives each line a verdict and the claim ids behind it.

Merge (per line, the worst wins; disagreement is shown, never resolved silently):
  contradicted / unsupported (AI or assertion+subject)  -> critical: blocks Gate 2 unless the owner overrides that line
                                                           citing a research claim id or a source URL
  keyword fires but the AI disagrees                    -> major "checks disagree": the owner must look (acknowledge)
  uncertain                                             -> major: the owner must acknowledge it
  attributed                                            -> info (keep the attribution)
"""
from __future__ import annotations
import re

from ..studio import checks

ATTRIB = ['يقولون', 'يقال', 'يُقال', 'قيل', 'شاع', 'بحسب', 'حسب', 'وفق', 'وفقًا', 'تقول', 'يقول', 'قالت', 'قال', 'زعم', 'زعمت', 'ادعت', 'ادّعت',
          'وصفتها', 'قدّمتها', 'قدمتها', 'أعلنت', 'روت', 'شهادتها', 'رواية', 'يعتقد', 'يظن', 'say', 'claimed', 'according']
NEG = ['لم', 'لا', 'ما', 'ليس', 'ليست', 'لن', 'not', 'never', 'no']
KINDS = [
    ('first_time', re.compile(r'(?:^|\s)(?:[وفبل]?(?:ال)?)?(?:أول|أوّل|اول)\s+مر[ةه]')),
    ('first', re.compile(r'(?:^|\s)[وفبلك]?(?:ال)?(?:أول|أوّل|اول|أولى|الأولى|الاولى)(?:\s|$)')),
    ('invent', re.compile(r'(?<!براءة\s)(?<!براءات\s)(?:اخترع|ابتكر|مخترع|مبتكر)')),
    ('pioneer', re.compile(r'(?:رائد|رائدة|رواد|سبّاق|سباق|السبّاقة|السباقة)')),
    ('era', re.compile(r'(?:بدأ|بداية|بدأت)\s+(?:عصر|زمن|عهد)')),
    ('only', re.compile(r'(?:^|\s)[وفبل]?(?:ال)?(?:وحيد|وحيدة|وحدها|وحده)(?:\s|$)')),
    ('oldest', re.compile(r'(?:أقدم|الأقدم|اقدم)')),
    ('nothing_before', re.compile(r'قبل')),
    ('en', re.compile(r'\b(?:first|invented|inventor|pioneer|only|oldest)\b', re.I)),
]


def key(w: str) -> str:
    """A rough root key for subject matching: no tashkeel, no proclitics, no common suffixes, first four letters."""
    b = checks.bare(w)
    b = re.sub(r'^[وف]', '', b) if len(b) > 4 else b
    b = re.sub(r'^(?:بال|كال|فال|وال|لل|ال|ب|ك|ل)', '', b) if len(b) > 4 else b
    b = re.sub(r'(?:ات|ون|ين|ها|هم|ة|ه|ي|ً)$', '', b) if len(b) > 4 else b
    return b[:4]


def _subject(claim: dict) -> set[str]:
    ws = []
    for p in claim.get('patterns', []):
        ws += checks.words(p)
    out = {key(w) for w in ws if len(checks.bare(w)) >= 3}
    drop = {key(x) for x in ('أول', 'اخترعت', 'اخترع', 'مضادة', 'صنعت', 'العالم')}
    return {k for k in out if k not in drop and len(k) >= 3}


def _clauses(text: str, sentences=False) -> list[str]:
    """Clauses (or sentences) that assert something: a question («أول ساعة مقاومة للماء؟») asks, it does not claim."""
    rx = re.compile(r'([.!?؟…]+)') if sentences else re.compile(r'([،,.؛;!?؟…]+|\s(?:لكن|لكنّ|بل|والحقيقة|الحقيقة)\s)')
    bits = rx.split(' ' + text + ' ')
    out = []
    for i in range(0, len(bits), 2):
        delim = bits[i + 1] if i + 1 < len(bits) else ''
        if '?' in delim or '؟' in delim: continue
        out.append(bits[i])
    return out


def assertions(text: str) -> list[dict]:
    """Priority / invention assertions per clause (per sentence for "nothing before X", which often spans a comma),
    with whether each is attributed or negated."""
    out = []
    parts = [(c, False) for c in _clauses(text)] + [(s, True) for s in _clauses(text, sentences=True)]
    for clause, sentence in parts:
        if not clause.strip(): continue
        flat = ' ' + clause.strip() + ' '
        ws = [checks.bare(w) for w in checks.words(clause)]
        for kind, rx in KINDS:
            if (kind == 'nothing_before') != sentence: continue
            m = rx.search(flat)
            if not m: continue
            if kind == 'first' and (KINDS[0][1].search(flat) or re.search(r'(?:أول|اول)\s+ما(?:\s|$)', flat)):
                continue                                        # «أول مرة» is its own kind; «أول ما» = 'the first thing that'
            neg = any(w in NEG for w in ws)
            if kind == 'nothing_before' and not neg:
                continue                                        # «قبل أويستر كانت هناك…» asserts nothing about priority
            before = checks.bare(flat[:m.start()])
            attributed = any(re.search(r'(^|\s)[وفبل]?' + re.escape(checks.bare(a)) + r'(\s|$)', before) for a in ATTRIB)
            negated = kind != 'nothing_before' and any(re.search(r'(^|\s)' + n + r'(\s|$)', ' '.join(before.split()[-2:])) for n in NEG)
            out.append({'kind': kind, 'phrase': m.group(0).strip(), 'clause': clause.strip(), 'attributed': attributed, 'negated': negated})
    return out


def subject_hits(clause: str, research: dict) -> list[str]:
    """Avoid-claims whose subject this clause talks about (two or more subject words in common)."""
    ks = {key(w) for w in checks.words(clause) if len(checks.bare(w)) >= 3}
    return [c['id'] for c in (research or {}).get('claims', []) if c.get('status') == 'avoid' and len(ks & _subject(c)) >= 2]


SEV = {'critical': 3, 'major': 2, 'minor': 1, 'info': 0}


def merge(lines: list[dict], research: dict, keyword: list[dict], ai: dict) -> dict:
    """Per line: {verdict, severity, why[], claims[], sources[], signals{}}. `keyword` is checks.check_version output,
    `ai` the fact checker's {'lines': {id: {verdict, claims, note}}}."""
    by = {c['id']: c for c in (research or {}).get('claims', [])}
    out = {}
    for ln in lines:
        lid, text = ln['id'], ln['text']
        kw = [f for f in keyword if f['line'] == lid and f['code'] == 'CLAIM_UNSUPPORTED']
        a = (ai or {}).get('lines', {}).get(lid) or {'verdict': 'uncertain', 'claims': [], 'note': 'the fact checker gave no verdict'}
        ass = [x for x in assertions(text) if not x['attributed'] and not x['negated']]
        strong = [x for x in ass if x['kind'] != 'first_time' and subject_hits(x['clause'], research)]
        why, sev, verdict = [], 'info', a['verdict']
        def worse(s, w):
            nonlocal sev
            why.append(w)
            if SEV[s] > SEV[sev]: sev = s
        if a['verdict'] in ('contradicted', 'unsupported'):
            worse('critical', f"fact checker: {a['verdict']} — {a.get('note', '')}")
        if strong:
            verdict = 'contradicted'
            worse('critical', f"asserts «{strong[0]['phrase']}» about what the research marks avoid ({', '.join(subject_hits(strong[0]['clause'], research))})")
        if kw and a['verdict'] not in ('contradicted', 'unsupported') and not strong:
            verdict = 'disputed'
            worse('major', 'the research rule flags this line but the fact checker does not: read it and decide')
        elif kw:
            why.append('research rule: ' + kw[0]['detail'][:160])
        if a['verdict'] == 'uncertain' and not strong:
            worse('major', 'uncertain: ' + (a.get('note') or 'no source found'))
        elif ass and a['verdict'] in ('supported',) and not any(by.get(c, {}).get('status') == 'verified' for c in a.get('claims', [])):
            verdict = 'uncertain'
            worse('major', f"asserts «{ass[0]['phrase']}» but no verified claim backs it")
        if a['verdict'] == 'attributed':
            worse('info', 'attributed: keep the attribution words')
        claims = [c for c in a.get('claims', []) if c in by]
        out[lid] = {'verdict': verdict, 'severity': sev if why else 'none', 'why': why, 'claims': claims,
                    'sources': sorted({s for c in claims for s in by[c].get('sources', [])}),
                    'signals': {'keyword': bool(kw), 'assertions': ass, 'ai': a}}
    return out


def override_ok(note: str, research: dict) -> bool:
    """An override must point at evidence: a research claim id (c4) or a source URL, not just a sentence."""
    ids = {c['id'] for c in (research or {}).get('claims', []) if c.get('status') in ('verified', 'attributed')}
    return bool(re.search(r'https?://\S+\.\S+', note or '')) or any(re.search(r'(^|\W)' + re.escape(i) + r'(\W|$)', note or '') for i in ids)
