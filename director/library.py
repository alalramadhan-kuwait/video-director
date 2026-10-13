"""Pronunciation library: one format for every project, scoped, versioned, provider-aware.

An entry describes how ONE term is said, independently of how any one voice engine wants it written:

    id: steel
    scope: brand:timekeeper          # global | brand:<id> | series:<id> | project:<id>
    status: approved                 # proposed | imported | approved | rejected
    surface: ستيل                    # the bare Arabic word(s) as written in the script, WITHOUT the article
    article: keep                    # keep: when the script has «الـ», the spoken form must keep it
    providers:
      elevenlabs: {mode: keep_arabic}             # send the Arabic word as written (article survives)
      habibi:     {mode: spoken, spoken: Steel}   # replace the word with a Latin respelling
      fasih:      {mode: stem, stem: سْتِيل}       # replace with a fully diacritized stem
    source: {file: video/royal-oak/tts_habibi.py, key: الستيل}

Matching is token-based and never a blind string replace:
  * diacritics in the script are ignored for matching and preserved outside the match;
  * a proclitic chain (و/ف + ب/ل/ك + ال, or لل) on the first word is recognised and kept;
  * multi-word surfaces win over shorter ones (longest match first);
  * Latin words in the script are left alone.
"""
from __future__ import annotations
import hashlib, json, re
from dataclasses import dataclass, field
from pathlib import Path
import yaml

from .vendor.arabic import strip

ARABIC_TOKEN = re.compile(r'[ء-يً-ْٰـ]+')
PROCLITIC = re.compile(r'^(?P<conj>[وف]?)(?:(?P<ll>لل)|(?P<prep>[بلك]?)(?P<art>ال)?)')
SCOPE_RE = re.compile(r'^(global|brand:[\w-]+|series:[\w-]+|project:[\w-]+)$')
STATUSES = {'proposed', 'imported', 'approved', 'rejected'}
MODES = {'keep_arabic', 'spoken', 'stem'}


def bare(s: str) -> str:
    """Letters only, with alef forms folded, for matching (never for output)."""
    s = strip(s)
    return re.sub('[أإآ]', 'ا', s)


@dataclass
class Entry:
    id: str
    scope: str
    surface: str
    status: str = 'proposed'
    article: str = 'keep'
    providers: dict = field(default_factory=dict)
    lines: list | None = None          # restrict to these script line ids (line-level overrides)
    source: dict | None = None
    approved: dict | None = None
    note: str = ''

    @property
    def words(self):
        return [bare(w) for w in re.split(r'[\s\-]+', self.surface.strip()) if w]


@dataclass
class Match:
    entry: Entry
    start: int          # char offset in the original text (start of the first token, including proclitics)
    end: int            # char offset after the last token
    prefix: str         # the proclitic letters exactly as written (with their diacritics)
    has_article: bool
    prefix_noart: str   # the proclitics without the article (what survives a Latin respelling)
    text: str           # the matched text as written


@dataclass
class Finding:
    code: str           # ARTICLE_DROPPED | UNAPPROVED_ENTRY | NO_PROVIDER_RULE
    severity: str       # critical | major | minor | info
    line: str | None
    entry: str
    detail: str


class Library:
    def __init__(self, entries: list[Entry], name='library'):
        self.name = name
        self.entries = entries
        self.errors = self.validate()

    # ---------------------------------------------------------------- loading
    @classmethod
    def load(cls, *paths, scopes: set[str] | None = None):
        """Load one or more YAML files. `scopes` keeps only entries whose scope is listed (plus 'global'),
        which is how a Time Keeper project never sees Diabetes History entries and vice versa."""
        entries = []
        for p in paths:
            data = yaml.safe_load(Path(p).read_text(encoding='utf-8')) or {}
            for raw in data.get('entries', []):
                e = Entry(**raw)
                if scopes is None or e.scope == 'global' or e.scope in scopes:
                    entries.append(e)
        return cls(entries, name='+'.join(Path(p).stem for p in paths))

    def dump(self, path):
        rows = [{k: v for k, v in e.__dict__.items() if v not in (None, '', {}, [])} for e in self.entries]
        Path(path).write_text(yaml.safe_dump({'entries': rows}, allow_unicode=True, sort_keys=False), encoding='utf-8')

    @property
    def version(self) -> str:
        """Content hash of the approved entries: recorded on every take for traceability (not part of the take key)."""
        rows = sorted(json.dumps(e.__dict__, ensure_ascii=False, sort_keys=True) for e in self.entries)
        return hashlib.sha256('\n'.join(rows).encode()).hexdigest()[:16]

    def validate(self):
        errs, seen = [], set()
        for e in self.entries:
            if e.id in seen: errs.append(f'{e.id}: duplicate id')
            seen.add(e.id)
            if not SCOPE_RE.match(e.scope): errs.append(f'{e.id}: bad scope {e.scope!r}')
            if e.status not in STATUSES: errs.append(f'{e.id}: bad status {e.status!r}')
            if not e.surface or bare(e.surface) == '' : errs.append(f'{e.id}: surface must be Arabic')
            if bare(e.surface).startswith('ال'): errs.append(f'{e.id}: write the surface without «ال»; use article: keep')
            for prov, rule in (e.providers or {}).items():
                if rule.get('mode') not in MODES: errs.append(f'{e.id}/{prov}: mode must be one of {sorted(MODES)}')
                if rule.get('mode') == 'spoken' and not rule.get('spoken'): errs.append(f'{e.id}/{prov}: spoken text missing')
                if rule.get('mode') == 'stem' and bare(rule.get('stem', '')) != bare(e.surface).replace(' ', ''):
                    errs.append(f'{e.id}/{prov}: stem letters differ from surface')
        return errs

    # ---------------------------------------------------------------- matching
    def find(self, text: str, line: str | None = None) -> list[Match]:
        toks = [(m.start(), m.end(), m.group()) for m in ARABIC_TOKEN.finditer(text)]
        cands = [e for e in self.entries if e.status != 'rejected' and (e.lines is None or line in e.lines)]
        cands.sort(key=lambda e: (-len(e.words), e.lines is None))  # longest surface first; line-level overrides win ties
        out, i = [], 0
        while i < len(toks):
            hit = None
            for e in cands:
                n = len(e.words)
                if i + n > len(toks): continue
                first = bare(toks[i][2])
                m = PROCLITIC.match(first)
                # try every proclitic split of the first token, longest stem first
                for cut in range(len(m.group(0)), -1, -1):
                    pre, stem = first[:cut], first[cut:]
                    if not PROCLITIC.fullmatch(pre) or stem != e.words[0]: continue
                    if all(bare(toks[i + k][2]) == e.words[k] and re.fullmatch(r'[\s\-]+', text[toks[i+k-1][1]:toks[i+k][0]])
                           for k in range(1, n)):
                        hit = (e, n, pre); break
                if hit: break
            if hit:
                e, n, pre = hit
                start, end = toks[i][0], toks[i + n - 1][1]
                art = 2 if pre.endswith('ال') else 1 if pre.endswith('لل') else 0
                out.append(Match(entry=e, start=start, end=end, prefix=_written_prefix(toks[i][2], len(pre)),
                                 has_article=art > 0, prefix_noart=_written_prefix(toks[i][2], len(pre) - art),
                                 text=text[start:end]))
                i += n
            else:
                i += 1
        return out

    # ---------------------------------------------------------------- provider input
    def prepare(self, text: str, provider: str, line: str | None = None, accept=('approved',)):
        """Return (provider_text, findings). Never edits the approved script; it only builds what is sent.
        accept lists the entry statuses whose rules are applied (default: approved only)."""
        findings, parts, pos = [], [], 0
        for m in self.find(text, line):
            e = m.entry
            rule = (e.providers or {}).get(provider)
            if e.status not in accept:
                findings.append(Finding('UNAPPROVED_ENTRY', 'minor', line, e.id,
                                        f'«{m.text}» matched a {e.status} entry; its rule is applied only after approval'))
                continue
            if rule is None:
                findings.append(Finding('NO_PROVIDER_RULE', 'info', line, e.id, f'no rule for {provider}; sent as written'))
                continue
            parts.append(text[pos:m.start])
            if rule['mode'] == 'keep_arabic':
                parts.append(m.text)
            elif rule['mode'] == 'stem':
                parts.append(m.prefix + rule['stem'])
            else:  # spoken (Latin or other respelling)
                if m.has_article and e.article == 'keep' and not rule.get('article_ok'):
                    findings.append(Finding('ARTICLE_DROPPED', 'major', line, e.id,
                        f'«{m.text}» has the article but {provider} receives «{rule["spoken"]}»: the «الـ» will not be heard. '
                        f'Use keep_arabic for this line (the old _arabic list) or approve article_ok.'))
                keep = m.prefix_noart                      # و/ف/ب/ل/ك stay, spaced from the Latin word (as tts_habibi did)
                parts.append((keep + ' ' if keep else '') + rule['spoken'])
            pos = m.end
        parts.append(text[pos:])
        return ''.join(parts), findings


def _written_prefix(token: str, n_letters: int) -> str:
    """The first n letters of `token` together with any diacritics attached to them."""
    if n_letters == 0: return ''
    seen = 0
    for i, ch in enumerate(token):
        if strip(ch):
            seen += 1
            if seen > n_letters: return token[:i]
    return token
