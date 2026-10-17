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
          'وصفتها', 'قدّمتها', 'قدمتها', 'أعلنت', 'روت', 'شهادتها', 'رواية', 'يعتقد', 'يظن', 'يزعم', 'تزعم', 'زعموا', 'يشاع', 'يدعي', 'تدعي',
          'يروى', 'يروج', 'تروج', 'say', 'says', 'claimed', 'claims', 'according', 'allegedly', 'supposedly']
NEG = ['لم', 'لا', 'ما', 'ليس', 'ليست', 'لن', 'not', 'never', 'no']
# a universal word: «لم تسبق رولكسَ أيُّ شركة», «قبل رولكس كانت كل الساعات…», "nobody … before"
UNIVERSAL = re.compile(r'(?:^|\s)(?:[وفبل]?(?:اي|ايّ|احد|كل|جميع|شيء)|ما\s+من|لا\s+شيء)(?:\s|$)|\b(?:nobody|no\s+one|none|nothing|no\s+other|all|every|any)\b', re.I)
# every pattern runs on checks.bare(text): no tashkeel, every hamza-alef written ا
KINDS = [
    ('first_time', re.compile(r'(?:^|\s)(?:[وفبل]?(?:ال)?)?اول\s+مر[ةه]')),
    ('first', re.compile(r'(?:^|\s)[وفبلك]?(?:ال)?(?:اول|اولى|الاولى)(?:\s|$)')),
    ('invent', re.compile(r'(?<!براءة\s)(?<!براءات\s)(?:اخترع|اختراع|ابتكر|ابتكار|مخترع|مبتكر|ابتدع|مبتدع|اوجد|من\s+العدم)')),
    ('pioneer', re.compile(r'(?:رائد|رائدة|رواد|ريادة|سباقا|سباقة|سباقين|السباقة|سباق\s+الى|السباق\s+الى|الاسبق|اسبق|صاحب(?:ة)?\s+السبق|السبق\s+في|باكورة)')),
    ('origin', re.compile(r'(?:(?:ولد|ولدت|نشا|نشات|ظهر|ظهرت|خرج|خرجت)\s+(?:\S+\s+){0,2}?على\s+يد|(?:يرجع|يعود|ترجع|تعود)\s+اصل|اصلها\s+الى|(?:ام|اب|ابو)\s+(?:هذا|هذه)\s+(?:الصنف|النوع|الفكرة)|مهد\s+(?:الساعات|الفكرة)|(?:بدا|بدات)\s+(?:بها|به|معها|معه)\s+(?:تاريخ|قصة))')),
    ('credit', re.compile(r'(?:صاحب(?:ة)?\s+الفضل|الفضل\s+في|يعود\s+الفضل|بفضل\s+\S+\s+صارت)')),
    ('era', re.compile(r'(?:بدا|بداية|بدات|دشن|دشنت|دشّن|دشّنت|افتتح|افتتحت|اطلق|اطلقت|فتح|فتحت)\s+(?:\S+\s+){0,2}?(?:عصر|زمن|عهد|حقبة)')),
    ('only', re.compile(r'(?:^|\s)[وفبل]?(?:ال)?(?:وحيد|وحيدة|وحدها|وحده)(?:\s|$)')),
    ('oldest', re.compile(r'(?:اقدم|الاقدم)')),
    ('nothing_before', re.compile(r'(?:قبل|سبق|يسبق|تسبق|سبقت|حتى\s+(?:جاء|جاءت|ظهر|ظهرت|صنع|صنعت|قدم|قدمت)|الى\s+ان\s+(?:جاء|جاءت|ظهر|ظهرت))')),
    ('en', re.compile(r'\b(?:first(?:-ever)?(?!\s+(?:part|year|time|page|half|chapter|episode|step|day|week|month|minute|second|section|scene|look|thing)s?\b)|invent(?:ed|or|ion)?|pioneer(?:ed|ing|s)?|came\s+up\s+with|originated|oldest|(?:father|mother|birth)\s+of|(?:no\s*one|nobody)\s+else|owe\s+.+\s+to)\b', re.I)),
    ('en_only', re.compile(r'\bthe\s+only\b(?!\s+(?:difference|change|thing|part|reason|way)\b)', re.I)),
    ('en_before', re.compile(r'\b(?:before|until|till)\b', re.I)),
]
SENTENCE_KINDS = ('nothing_before', 'en_before')
COPULA = {'كان', 'كانت', 'هي', 'هو', 'تكون', 'يكون', 'اصبح', 'اصبحت', 'صار', 'صارت', 'تعد', 'يعد', 'تعتبر', 'يعتبر', 'ظلت', 'بقيت'}
SUPERLATIVE_TAIL = re.compile(r'^\s*(?:في\s+(?:العالم|التاريخ)|من\s+نوع|عالميا|على\s+الاطلاق|التي|الذي|اللتي|اللذي|بين)')


def _ordinal(flat: str, m) -> bool:
    """«في عامها الأول», «الحرب العالمية الأولى», «الجزء الأول»: a definite «الأول/الأولى» right after a noun is an
    ordinal (which year, which part), not a priority claim, unless a copula comes before it («كانت الأولى») or a
    superlative tail follows («الأولى في العالم», «الأولى التي…»)."""
    tok = m.group(0).strip()
    if not re.match(r'^[وفبلك]?ال', tok): return False
    prev = flat[:m.start()].split()
    if not prev or prev[-1] in COPULA or prev[-1] in NEG: return False
    if SUPERLATIVE_TAIL.search(flat[m.end():]): return False
    return True


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
    rx = (re.compile(r'([.!?؟…](?:\s*[.!?؟…])*)') if sentences else
          re.compile(r'([،,.؛;!?؟…](?:\s*[،,.؛;!?؟…])*|\s(?:لكن|لكنّ|بل|والحقيقة|الحقيقة)\s)'))
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
        flat = ' ' + checks.bare(clause.strip()) + ' '
        ws = flat.split()
        for kind, rx in KINDS:
            if (kind in SENTENCE_KINDS) != sentence: continue
            m = rx.search(flat)
            if not m: continue
            if kind == 'first' and (KINDS[0][1].search(flat) or re.search(r'اول\s+ما(?:\s|$)', flat) or _ordinal(flat, m)):
                continue                                        # «أول مرة» is its own kind; «أول ما» = 'the first thing that'
            if kind == 'only' and _ordinal(flat, m):
                continue                                        # «الفرق الوحيد بين النموذجين»: which difference, not a claim
            if kind == 'first_time' and re.search(r'(?:للعالم|في\s+العالم|في\s+التاريخ|للبشرية)', flat):
                kind = 'first'                                  # «قدّمت للعالم لأول مرة …» is a priority claim
            neg = any(w in NEG for w in ws) or bool(re.search(r"\b(?:never|no|not|nobody|none)\b|n't", flat, re.I))
            if kind in SENTENCE_KINDS and not (neg or UNIVERSAL.search(flat)):
                continue                                        # «قبل أويستر كانت هناك…» asserts nothing about priority
            if kind == 'nothing_before' and re.search(r'(?:^|\s)(?:[وف]?ل[مان]|ليس|ليست)\s+(?:تكن|يكن|تكون|يكون)?\s*(?:الاسبق|اول|السباقة)', flat):
                continue                                        # «لم تكن الأسبق» denies priority (the 'first' kinds see it as negated)
            before = flat[:m.start()]
            attributed = any(re.search(r'(^|\s)[وفبل]?' + re.escape(checks.bare(a)) + r'(\s|$)', before, re.I) for a in ATTRIB)
            negated = kind not in SENTENCE_KINDS and any(re.search(r'(^|\s)' + n + r'(\s|$)', ' '.join(before.split()[-4:])) for n in NEG)
            out.append({'kind': kind, 'phrase': m.group(0).strip(), 'clause': clause.strip(), 'attributed': attributed, 'negated': negated})
    return out


def subject_hits(clause: str, research: dict) -> list[str]:
    """Avoid-claims whose subject this clause talks about (two or more subject words in common)."""
    ks = {key(w) for w in checks.words(clause) if len(checks.bare(w)) >= 3}
    return [c['id'] for c in (research or {}).get('claims', []) if c.get('status') == 'avoid' and len(ks & _subject(c)) >= 2]


SEV = {'critical': 3, 'major': 2, 'minor': 1, 'info': 0}
IDIOM = re.compile(r'الصفحة الأولى|الصفحه الاولى|للمرة الأولى في حياتها|front page')     # set phrases, not priority claims


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
        prio = [x for x in ass if x['kind'] != 'first_time' and not IDIOM.search(x['clause'])]
        backed = any(by.get(c, {}).get('status') in ('verified', 'attributed') for c in a.get('claims', []))
        if prio and not strong and not backed:
            verdict = 'unsupported'
            worse('critical', f"asserts «{prio[0]['phrase']}» (a first / invention / priority claim) with no verified source behind it")
        elif a['verdict'] == 'uncertain' and not strong:
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


URL = re.compile(r'https?://([^\s/]+)[^\s]*')


def _real_host(h: str) -> bool:
    """A link to a real-looking site: a name of 3+ letters and a 2+ letter ending (not «a.bc», an IP or localhost)."""
    parts = h.lower().split(':')[0].split('.')
    return len(parts) >= 2 and re.fullmatch(r'[a-z]{2,}', parts[-1]) is not None and any(len(x) >= 3 and re.search('[a-z]', x) for x in parts[:-1])


def override_ok(note: str, research: dict, connected=None) -> bool:
    """An override must point at evidence AND say in a sentence why the check is wrong here (at least 12 characters and
    3 words besides the citation). Evidence is either a verified/attributed research claim that is connected to THIS
    line (`connected`: the claims the writer or the fact checker gave for it; any claim of the file when not known), or
    a link to a real-looking site (recorded as the owner's source, shown again at Gate 5 and on the paid plan).
    Whether the cited claim really says what the line says is still the owner's judgement: the machine cannot read
    the English claim against the Arabic sentence. That needs the real AI fact checker."""
    note = note or ''
    ids = {c['id'] for c in (research or {}).get('claims', []) if c.get('status') in ('verified', 'attributed')}
    if connected is not None: ids &= set(connected)
    urls = [m.group(0) for m in URL.finditer(note) if _real_host(m.group(1))]
    cites = urls + [i for i in ids if re.search(r'(^|\W)' + re.escape(i) + r'(\W|$)', note)]
    if not cites: return False
    rest = URL.sub(' ', note)
    for c in cites: rest = rest.replace(c, ' ')
    rest = re.sub(r'(^|\W)c\d+(\W|$)', ' ', rest)                    # other claim ids are not words of a reason
    words = [w for w in re.findall(r'\w+', rest) if len(w) >= 2]
    return len(rest.strip()) >= 12 and len(words) >= 3 and len(set(''.join(words))) >= 5


def connected_claims(cp_line_check: dict | None, writer_claims) -> list[str]:
    """The research claims linked to one line: what the writer cited for it and what the fact checker matched."""
    return sorted(set((cp_line_check or {}).get('claims') or []) | set(writer_claims or []))
