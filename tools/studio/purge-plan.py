#!/usr/bin/env python3
"""H3 + v5 (L3): the weekly purge, by id. Two modes, both read-only on their inputs:
  ask:    python3 purge-plan.py ask    --films <dir> [--inbox <dir>] [--prev <old studio-purge.json>] --now <ISO> --out <dir>
          -> studio-purge.json (the question to write to studio/purge)
  delete: python3 purge-plan.py delete --films <dir> --inbox <dir> [--ideas <dir>] --purge <studio-purge.json> --out <dir>
          -> delete-list.json
  recheck: python3 purge-plan.py recheck --record <fresh films/<id>.json> --purge <studio-purge.json>
          -> exit 0 if this record may still be deleted now, 1 if not (v6 L3: re-read just before each delete)
ask lists films hidden 30+ days, names/kind/version taken from the film records, and leaves out any id he kept («لا», or not
ticked) in the last 30 days.
delete lists ONLY ids that are in his «yes» row for this question (asked_at) with a non-empty `ids`, are in the question, are
still hidden, and were hidden at least 30 days before the question was asked. For each, the exact files it names: every
/_blob/<id> anywhere in the record, and (v8, M5) the published paths in its own file fields (`video`, `final`, `slides`,
`prev_video`, `poster`, `voice.*`, `posted.*`, `history[].video|final|slides`), each as the exact string, never a pattern. Any
file that anything staying still mentions is kept: another film, an idea, or an unhandled inbox row, anywhere in any text or
URL (v6 L3). Names and id prefixes are never used to match anything: `rubies` never reaches `film/rubies-engraving-v1.mp4`."""
import json, glob, os, sys, argparse
from datetime import datetime, timedelta, timezone
ap = argparse.ArgumentParser(); ap.add_argument('mode', choices=['ask', 'delete', 'recheck']); ap.add_argument('--ideas'); ap.add_argument('--record'); ap.add_argument('--films'); ap.add_argument('--inbox')
ap.add_argument('--purge'); ap.add_argument('--prev'); ap.add_argument('--now'); ap.add_argument('--out'); a = ap.parse_args()
load = lambda p: (lambda j: j.get('data', j))(json.load(open(p)))
import re
ts = lambda s: datetime.fromisoformat(str(s).replace('Z', '+00:00'))
DAYS = timedelta(days=30)
if a.mode == 'recheck':                                                # v6 (L3): the fresh record, read just before its delete
    q = json.load(open(a.purge)); f = load(a.record)
    ok = isinstance(q.get('asked_at'), str) and f.get('hidden') is True and isinstance(f.get('hidden_at'), str) and ts(f['hidden_at']) <= ts(q['asked_at']) - DAYS
    print('ok to delete' if ok else 'skip: not hidden any more, or hidden too recently'); sys.exit(0 if ok else 1)
films = {os.path.basename(p)[:-5]: load(p) for p in sorted(glob.glob(os.path.join(a.films, '*.json')))}
rows = [load(p) for p in glob.glob(os.path.join(a.inbox, '*.json'))] if a.inbox else []
ideas = [load(p) for p in glob.glob(os.path.join(a.ideas, '*.json'))] if a.ideas else []
os.makedirs(a.out, exist_ok=True)
purge_rows = lambda: [r for r in rows if r.get('kind') == 'answer' and r.get('key') == 'purge' and isinstance(r.get('asked_at'), str)]
BLOB = re.compile(r'/_blob/([A-Za-z0-9_-]+)')
def blobs(x):                                                      # v6 (L3): every /_blob/<id> named anywhere: a path, a full URL, inside a sentence, or a key
    if isinstance(x, str): return {'/_blob/' + m for m in BLOB.findall(x)}
    if isinstance(x, list): return set().union(*map(blobs, x)) if x else set()
    if isinstance(x, dict): return set().union(*map(blobs, x.values()), *map(blobs, x.keys())) if x else set()
    return set()
FILE_FIELDS = ('video', 'final', 'slides', 'prev_video', 'poster')
PUB = re.compile(r'^(?!https?:|data:|blob:|//)/?[\w.-]+(?:/[\w.%-]+)*\.(?:mp4|mov|m4v|png|jpe?g|webp|gif|mp3|m4a|wav|aac)(?:\?.*)?$', re.I)
def norm(u): return u.split('?')[0].split('#')[0].lstrip('/')
def strings(x):                                                     # every string in a value, keys too
    if isinstance(x, str): return [x]
    if isinstance(x, list): return [s for y in x for s in strings(y)]
    if isinstance(x, dict): return [s for k, y in x.items() for s in strings(k) + strings(y)]
    return []
def own_paths(f):                                                   # v8 (M5): the published files this record names in its own file fields
    vals = [f.get(k) for k in FILE_FIELDS] + [f.get('voice'), f.get('posted')]
    vals += [{k: h.get(k) for k in ('video', 'final', 'slides')} for h in (f.get('history') or []) if isinstance(h, dict)]
    return {norm(s) for s in strings(vals) if isinstance(s, str) and PUB.match(s.strip()) and '/_blob/' not in s}
def files_of(f): return blobs(f) | own_paths(f)
def named_by(things):                                               # every file a staying thing names, as normalized strings
    out = set()
    for s in strings(things):
        out |= {'/_blob/' + m for m in BLOB.findall(s)}
        out |= {norm(m.group(0)) for m in re.finditer(r'(?<![\w/.-])/?[\w.-]+(?:/[\w.%-]+)+\.(?:mp4|mov|m4v|png|jpe?g|webp|gif|mp3|m4a|wav|aac)', s, re.I)}
    return out
if a.mode == 'ask':
    now = ts(a.now) if a.now else datetime.now(timezone.utc)
    prev = json.load(open(a.prev)) if a.prev and os.path.exists(a.prev) else None
    kept = {}                                                        # id -> when he kept it
    for r in purge_rows():
        if not r.get('at') or ts(r['at']) < now - DAYS: continue
        asked = r.get('asked') or ([x['id'] for x in prev.get('films', [])] if prev and prev.get('asked_at') == r.get('asked_at') else [])
        chosen = set(r.get('ids') or []) if r.get('answer') == 'yes' else set()
        for i in asked:
            if i not in chosen: kept[i] = r['at']
    old = [(i, f) for i, f in films.items() if f.get('hidden') and f.get('hidden_at') and ts(f['hidden_at']) <= now - DAYS and i not in kept]
    doc = {'asked_at': now.isoformat().replace('+00:00', 'Z'), 'status': 'open', 'q': 'مخفية أكثر من 30 يوم: تختار وش ينمسح',
           'films': [{'id': i, 'name': f.get('name') or i, 'kind': f.get('kind') or ('carousel' if f.get('slides') else 'reel'), 'version': f.get('version') or ''} for i, f in old]}
    json.dump(doc, open(os.path.join(a.out, 'studio-purge.json'), 'w'), ensure_ascii=False, indent=1)
    print(f'{len(old)} films in the question; left out (kept in the last 30 days): {sorted(kept)}'); sys.exit(0)
q = json.load(open(a.purge))
if not isinstance(q.get('asked_at'), str): print('the question has no asked_at: nothing to do'); json.dump({'asked_at': None, 'answer_row': None, 'delete': [], 'kept': []}, open(os.path.join(a.out, 'delete-list.json'), 'w')); sys.exit(0)
yes = sorted([r for r in purge_rows() if r.get('asked_at') == q['asked_at']], key=lambda r: r.get('at', ''), reverse=True)
yes = [r for r in yes if r.get('answer') == 'no' or (r.get('answer') == 'yes' and isinstance(r.get('ids'), list) and r['ids'])]   # a yes without ids is no answer
out = {'asked_at': q['asked_at'], 'answer_row': None, 'delete': [], 'kept': []}
if yes and yes[0].get('answer') == 'yes':
    r = yes[0]; out['answer_row'] = {k: r.get(k) for k in ('at', 'ids', 'via')}
    asked, cut = {x['id'] for x in q['films']}, ts(q['asked_at']) - DAYS
    go = []
    for i in r['ids']:
        f = films.get(i)
        if i not in asked: why = 'مو بالسؤال'
        elif not f: why = 'ما له سجل'
        elif not f.get('hidden'): why = 'انرجع (مو مخفي)'
        elif not f.get('hidden_at') or ts(f['hidden_at']) > cut: why = 'ما صار له 30 يوم مخفي قبل السؤال'
        else: go.append(i); continue
        out['kept'].append({'id': i, 'why': why})
    stay_things = [f for i, f in films.items() if i not in go] + ideas + [r for r in rows if not r.get('handled_at')]
    stay_strings = strings(stay_things)
    def named(p):                                                   # v9 (L3): any staying string holds it as a whole path, full URLs and ./ included
        return any(re.search(r'(?<![\w.%-])' + re.escape(p.lstrip('/')) + r'(?![\w.%-])', x) for x in stay_strings)
    stays = named_by(stay_things) | {p for i in go for p in files_of(films[i]) if named(p)}
    for i in go:
        mine = files_of(films[i])
        out['delete'].append({'id': i, 'why': 'بجوابك، وللحين مخفي من 30 يوم قبل السؤال', 'files': sorted(mine - stays), 'files_kept': sorted(mine & stays)})
    for x in q['films']:
        if x['id'] not in r['ids']: out['kept'].append({'id': x['id'], 'why': 'ما اخترته'})
elif yes: out['answer_row'] = {'answer': yes[0].get('answer')}
json.dump(out, open(os.path.join(a.out, 'delete-list.json'), 'w'), ensure_ascii=False, indent=1)
print(f"delete {len(out['delete'])}: {[x['id'] for x in out['delete']]}; keep {len(out['kept'])}: {[(x['id'], x['why']) for x in out['kept']]}; "
      f"files kept (shared): {sorted({b for x in out['delete'] for b in x['files_kept']})}")
