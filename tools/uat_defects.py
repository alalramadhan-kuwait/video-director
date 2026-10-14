"""Stage H: plant known defects in a DISPOSABLE COPY of the project, render it, run the independent review, and check
that every defect is found with its scene, timecode, evidence, severity and fix. Then accept/dismiss findings in the
copy and prove that approved art, takes and the storyboard did not change.

    PYTHONPATH=. python3 tools/uat_defects.py var/dashboard-uat rolex-oyster var/uat/defects
"""
import copy, hashlib, json, shutil, sys
from pathlib import Path

from director.studio.store import Studio
from director.studio import storyboard, review, jobs
from director.studio.storyboard import VOICE_AT

src, pid, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
var = out / 'var'
if var.exists():
    for p in var.rglob('*'):
        if p.is_file(): p.chmod(0o644)
    shutil.rmtree(var)
var.mkdir(parents=True)
shutil.copyfile(src / 'events.sqlite', var / 'events.sqlite')
shutil.copytree(src / 'studio', var / 'studio', ignore=shutil.ignore_patterns('work'))
S = Studio(var)
st0 = S.state(pid)
LOGO = 'tk-logo-512.png'

EXPECT = [  # (code, scene) every planted defect must produce
    ('STATIC_OPENING', 'cover'), ('YEAR_NOT_IN_RESEARCH', 'l4'), ('DRAWN_BRAND_WATCH', 'l11'), ('MISSING_ASSET', 'l12'),
    ('OVERLAP', 'l6'), ('CUT_BY_FRAME', 'l8'), ('OFF_BRAND_THEME', 'l13'), ('AV_SYNC', 'l3'), ('AV_SYNC', 'l7'),
    ('BANNER_LONG', 'l5'), ('LATIN_IN_CAPTIONS', 'l9'), ('WRONG_SIZE', None), ('DRAWING_UNLABELLED', 'l7'), ('ON_CAPTIONS', 'l2')]
PLANTED = {
    'cover': 'a frozen 1.6 s cover before the hook (Reels must open on a moving hook)',
    'l4': 'banner year changed 1922 → 1924 (not in the research)', 'l11': 'a drawn watch labelled ROLEX',
    'l12': 'the newspaper card replaced by an archival photo slot with no file', 'l6': 'two prints placed on top of each other',
    'l8': 'a card pushed half out of the frame', 'l13': 'Diabetes History navy (#1C3550) as the background',
    'l3': 'voice placed 0.8 s late against captions and visuals', 'l7': 'voice 0.8 s late; the drawing label removed',
    'l5': 'a 9-word banner', 'l9': 'a Latin word in the Arabic captions', 'size': 'exported at 720x1280 instead of 1080x1920',
    'l2': 'a print in the caption band'}


def inject(esb, work):
    sc = {s.get('id'): s for s in esb['scenes'] if s.get('id')}
    esb['scenes'].insert(0, {'id': 'cover', 'theme': 'tk-bone', 'floor': False, 'dur': 1.6, 'silent': True, 'transition': 'cut',
                             'elements': [{'type': 'text', 'text': 'رولكس أويستر', 'font': 'title', 'size': 90, 'x': 360, 'y': 600, 'still': True}]})
    sc['l4']['banner'] = 'رولكس · 1924'
    sc['l11']['elements'].append({'type': 'watch', 'brand': 'ROLEX', 'x': 360, 'y': 720, 'size': 200})
    sc['l12']['elements'] = [{'type': 'photo', 'asset': 'daily_mail_1927_11_24', 'desc': 'Daily Mail front page, 24 Nov 1927', 'w': 460, 'aspect': .8, 'x': 360, 'y': 560}]
    sc['l6']['elements'] += [{'type': 'photo', 'src': LOGO, 'w': 300, 'aspect': 1, 'x': 360, 'y': 560, 'polaroid': True, 'label': 'A'},
                             {'type': 'photo', 'src': LOGO, 'w': 300, 'aspect': 1, 'x': 390, 'y': 590, 'polaroid': True, 'label': 'B'}]
    sc['l8']['elements'].append({'type': 'card', 'x': 690, 'y': 560, 'w': 400, 'h': 200, 'title': 'خارج الإطار', 'tex': 'paper'})
    sc['l13']['theme'] = {'bg': '#1C3550', 'blot': ['#24405F', '#152A40'], 'floor': '#152A40', 'floorTop': '#24405F', 'capBg': '#FFF8EE', 'capInk': '#1C3550'}
    for k in ('l3', 'l7'):
        sc[k]['voiceAt'] = VOICE_AT + 0.8
    sc['l7']['elements'] = [e for e in sc['l7']['elements'] if 'توضيحي' not in str(e.get('text', ''))]
    sc['l5']['banner'] = 'براءة اختراع سويسرية مهمة جدًا لصانعين من لاشو دو فون'
    sc['l9']['words'] = [[t, 'Gleitze' if i == 4 else w] for i, (t, w) in enumerate(sc['l9']['words'])]
    sc['l2']['elements'].append({'type': 'photo', 'src': LOGO, 'w': 220, 'aspect': 1, 'x': 360, 'y': 1010, 'polaroid': True})
    return esb


def fingerprint(st):
    return hashlib.sha256(json.dumps({'art': st['art']['approved'], 'versions': {k: [(v['v'], v.get('status'), v['stills']) for v in c['versions']] for k, c in st['art']['concepts'].items()},
                                      'takes': {k: (t['status'], t['audio']) for k, t in st['voice']['takes'].items()},
                                      'storyboards': [s['file'] for s in st['storyboards']], 'scripts': [(s['v'], s['status'], s['file']) for s in st['scripts']]},
                                     sort_keys=True).encode()).hexdigest()


before = fingerprint(st0)
jobs.start(S, pid, 'render', 'draft', 'DEFECT COPY render', 5, storyboard.render, {'scale': 1.0, 'inject': inject}, sync=True)
st = S.state(pid)
r = st['renders'][-1]
assert r['state'] == 'ok', r
prof = S.profile('timekeeper'); other = [S.profile('diabetes-history')]
jobs.start(S, pid, 'review', 'review', 'review of the defect copy', 7, review.run,
           {'render_id': r['id'], 'profile': prof, 'other_profiles': other, 'research': S.research(pid), 'label': 'defects'}, sync=True)
st = S.state(pid)
rv = st['review']['runs'][-1]
F = [f for f in st['review']['findings'].values() if f['run'] == rv['id']]
rows = []
for code, scene in EXPECT:
    hit = [f for f in F if f['code'] == code and (scene is None or f['scene'] == scene)]
    rows.append({'planted': PLANTED.get(scene or 'size'), 'expect': f'{code}@{scene}', 'found': bool(hit),
                 'finding': hit[0] if hit else None})
expected_keys = {(c, s) for c, s in EXPECT}
extra = [f for f in F if (f['code'], f['scene']) not in expected_keys and not (f['code'], None) in expected_keys]
# decide in the copy: accept one, dismiss one; approved work must not change
acc = next(f for f in F if f['code'] == 'YEAR_NOT_IN_RESEARCH')
dis = next(f for f in F if f['code'] == 'BANNER_LONG')
S.act(pid, 'finding_decision', {'finding': acc['id'], 'decision': 'accepted'})
S.act(pid, 'finding_decision', {'finding': dis['id'], 'decision': 'dismissed', 'note': 'UAT: dismissed on purpose to check the history keeps it'})
st2 = S.state(pid)
after = fingerprint(st2)
res = {'render': {k: r[k] for k in ('id', 'seconds', 'render_s', 'size_mb')}, 'review': rv['id'], 'counts': rv['counts'],
       'detected': sum(x['found'] for x in rows), 'planted': len(rows), 'rows': rows,
       'extra_findings': [{k: f[k] for k in ('code', 'scene', 't', 'severity', 'detail')} for f in extra],
       'accepted_task': [t for t in st2['fix_tasks'] if t['finding'] == acc['id']],
       'dismissed_kept': st2['review']['findings'][dis['id']]['decision_note'],
       'approved_work_unchanged': before == after, 'copy_var': str(var)}
(out / 'defects.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')
for x in rows:
    f = x['finding']
    print(('FOUND ' if x['found'] else 'MISSED') + f" {x['expect']:<28} " + (f"{f['severity']:<8} t={f['t']} {f['detail'][:90]}" if f else x['planted']))
print('extra:', [(f['code'], f['scene']) for f in extra])
print('accepted→task:', bool(res['accepted_task']), ' dismissed kept:', res['dismissed_kept'][:30], ' approved work unchanged:', res['approved_work_unchanged'])
