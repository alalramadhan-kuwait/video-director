"""The owner's own edits to a carousel, word for word: python3 tools/carousel/edits.py <film record .json> …

The owner, 2 Nov 2026: «I want you to understand every change I'm doing in the carousel so it can be updated for the
future, to keep it as a reference and learn from it». Reads studio film records (as ArtifactData saves them with
out_dir) and prints each edit the owner made in the studio's text editor as a ready entry for
skills/reel-master/references/carousel-edits.md: where, the words before and after, and the owner's «ليش» when given.
Newer records carry the edits in `changes[].edits`; older ones are found by comparing `spec` with `history`."""
import json
import re
import sys
from pathlib import Path

FIELDS = {'top': 'السطر الأول', 'bottom': 'السطر الثاني', 'title': 'العنوان', 'name': 'الاسم', 'body': 'النص', 'ask': 'سؤال القارئ'}


def plain(html) -> str:
    return re.sub(r'<b>(.*?)</b>', r'**\1**', str(html or ''), flags=re.S).strip()


def diff(was: dict, now: dict, cap_was: str = '', cap_now: str = '') -> list[dict]:
    """Field by field, what changed between two specs (as the studio's edDiff does)."""
    out = []
    pairs = [('الغلاف', was.get('cover') or {}, now.get('cover') or {})]
    pairs += [(f'الشريحة {i}', (was.get('slides') or [{}] * i)[i - 1] if i <= len(was.get('slides') or []) else {}, s)
              for i, s in enumerate(now.get('slides') or [], 1)]
    for where, a, z in pairs:
        for key, field in FIELDS.items():
            if plain(a.get(key)) != plain(z.get(key)):
                out.append({'where': where, 'field': field, 'key': key, 'before': plain(a.get(key)), 'after': plain(z.get(key))})
    if (cap_was or '').strip() != (cap_now or '').strip():
        out.append({'where': 'الكابشن', 'field': 'الكابشن', 'key': 'caption', 'before': cap_was or '', 'after': cap_now or ''})
    return out


def wdiff(a: str, z: str) -> list[tuple[str, str]]:
    """The changed runs of words, [(before, after), …] (the studio's wdiff)."""
    A, Z = str(a or '').split(), str(z or '').split()
    L = [[0] * (len(Z) + 1) for _ in range(len(A) + 1)]
    for i in range(len(A) - 1, -1, -1):
        for j in range(len(Z) - 1, -1, -1):
            L[i][j] = L[i + 1][j + 1] + 1 if A[i] == Z[j] else max(L[i + 1][j], L[i][j + 1])
    out, i, j, cur = [], 0, 0, None
    while i < len(A) or j < len(Z):
        if i < len(A) and j < len(Z) and A[i] == Z[j]:
            if cur: out.append((' '.join(cur[0]), ' '.join(cur[1]))); cur = None
            i += 1; j += 1
        elif j < len(Z) and (i >= len(A) or L[i][j + 1] >= L[i + 1][j]):
            cur = cur or ([], []); cur[1].append(Z[j]); j += 1
        else:
            cur = cur or ([], []); cur[0].append(A[i]); i += 1
    if cur: out.append((' '.join(cur[0]), ' '.join(cur[1])))
    return out


def owner_edits(rec: dict) -> list[dict]:
    """[{film, version, at, why, edits}] newest first, for every version the owner saved in the studio."""
    rec = rec.get('data', rec)
    found, seen = [], set()
    for c in rec.get('changes') or []:
        if c.get('edits') is not None:
            found.append({'film': rec.get('name') or rec.get('id'), 'version': c.get('v'), 'at': c.get('at'), 'why': c.get('why', ''), 'edits': c['edits']})
            seen.add(c.get('v'))
    # Older saves (before edits were kept): their change line says «عدّلت النص بنفسك»; compare that version's spec with
    # the one before it, both found among the record and its history.
    states = [(rec.get('version'), rec.get('spec'), rec.get('caption', ''))] + [(h.get('version'), h.get('spec'), h.get('caption', '')) for h in rec.get('history') or []]
    for c in rec.get('changes') or []:
        if c.get('v') in seen or not any(str(w).startswith('عدّلت النص بنفسك') for w in c.get('what') or []):
            continue
        k = next((i for i, st in enumerate(states) if st[0] == c.get('v')), None)
        if k is None or k + 1 >= len(states) or not states[k][1] or not states[k + 1][1]:
            continue
        d = diff(states[k + 1][1], states[k][1], states[k + 1][2], states[k][2])
        if d:
            found.append({'film': rec.get('name') or rec.get('id'), 'version': c.get('v'), 'at': c.get('at'), 'why': '', 'edits': d})
    return found


def entry(e: dict) -> str:
    lines = [f"### {str(e['at'] or '')[:10]} · {e['film']} {e['version']}"]
    for d in e['edits']:
        runs = '، '.join(f'«{x or "—"}» ← «{y or "—"}»' for x, y in wdiff(d['before'], d['after']))
        lines.append(f"- **{d['where']} · {d['field']}:** {runs}")
        lines.append(f"  - was: {d['before']}\n  - now: {d['after']}")
    if e['why']: lines.append(f"- **ليش (the owner):** {e['why']}")
    lines.append('- **Lesson:** …\n- **Status:** watching')
    return '\n'.join(lines)


def main(argv=None) -> int:
    paths = (argv if argv is not None else sys.argv[1:])
    if not paths: print(__doc__); return 2
    for p in paths:
        for e in owner_edits(json.loads(Path(p).read_text(encoding='utf-8'))):
            print(entry(e) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
