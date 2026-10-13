"""Read-only importers: turn the existing dictionaries into library entries without executing or editing them.

Every imported entry gets status 'imported' and a `source` pointer; nothing is approved here.
"""
from __future__ import annotations
import ast, json, re
from pathlib import Path
import yaml
from .library import Entry, bare

_slug = lambda s, n=0: re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-') or f'term-{n}'


def habibi_pron(path, scope='brand:timekeeper', providers=('habibi', 'elevenlabs')) -> list[Entry]:
    """Parse the PRON dict literal out of video/royal-oak/tts_habibi.py WITHOUT importing the module
    (importing it creates folders as a side effect). Keys that differ only by «ال» become one entry."""
    tree = ast.parse(Path(path).read_text(encoding='utf-8'))
    pron = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(getattr(t, 'id', None) == 'PRON' for t in node.targets):
            pron = ast.literal_eval(node.value)
    if pron is None:
        raise ValueError('PRON not found')
    by_surface: dict[str, Entry] = {}
    for n, (ar, latin) in enumerate(pron.items()):
        if not re.search('[ء-ي]', ar):
            continue
        words = ar.split()
        surface = ' '.join([words[0][2:] if bare(words[0]).startswith('ال') and len(bare(words[0])) > 3 else words[0]] + words[1:])
        key = bare(surface)
        if key in by_surface:
            by_surface[key].source.setdefault('also', []).append(ar)
            continue
        rule = {'mode': 'spoken', 'spoken': latin}
        by_surface[key] = Entry(id=f'tk-{_slug(latin, n)}', scope=scope, surface=surface, status='imported',
                                providers={p: dict(rule) for p in providers},
                                source={'file': str(path), 'key': ar})
    out, ids = [], set()
    for e in by_surface.values():
        while e.id in ids: e.id += '-2'
        ids.add(e.id); out.append(e)
    return out


def keep_arabic_overrides(script_path, scope='project:royal-oak', provider='elevenlabs') -> list[Entry]:
    """The script's `_arabic` map ({line: [terms]}) becomes line-scoped keep_arabic entries."""
    data = json.loads(Path(script_path).read_text(encoding='utf-8'))
    out = []
    for line, terms in (data.get('_arabic') or {}).items():
        for t in terms:
            surface = t[2:] if bare(t).startswith('ال') else t
            out.append(Entry(id=f'keep-{line}-{_slug(surface, len(out)) if not re.search("[ء-ي]", surface) else len(out)}',
                             scope=scope, surface=surface, status='imported', lines=[line],
                             providers={provider: {'mode': 'keep_arabic'}},
                             source={'file': str(script_path), 'key': f'_arabic.{line}'}))
    return out


def arabic_tts_lexicon(path, scope='series:diabetes-history', provider='fasih') -> list[Entry]:
    """The arabic_tts YAML lexicon (match/stem/spoken/plain/contexts...). Context rules are kept verbatim in `note`
    for now; the Fasih adapter keeps using arabic_tts itself, so nothing about the existing workflow changes."""
    data = yaml.safe_load(Path(path).read_text(encoding='utf-8')) or {}
    out = []
    for n, e in enumerate(data.get('entries', [])):
        m = e.get('match', '')
        if not re.search('[ء-ي]', m):
            continue
        if e.get('spoken'):
            rule = {'mode': 'spoken', 'spoken': e['spoken']}
        elif e.get('stem') and not e.get('plain'):
            rule = {'mode': 'stem', 'stem': e['stem']}
        else:
            rule = {'mode': 'keep_arabic'}
        extra = {k: e[k] for k in ('contexts', 'avoid', 'protect', 'ending', 'kind', 'note', 'plain') if k in e}
        out.append(Entry(id=f'dh-{n:03d}', scope=scope, surface=m, status='imported', providers={provider: rule},
                         source={'file': str(path), 'index': n}, note=json.dumps(extra, ensure_ascii=False) if extra else ''))
    return out
