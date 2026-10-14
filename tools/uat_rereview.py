"""Re-run the reviewer on an existing render (no new render): PYTHONPATH=. python3 tools/uat_rereview.py VAR PID RENDER LABEL"""
import sys
from pathlib import Path
from director.studio.store import Studio
from director.studio import review, jobs
var, pid, rid, label = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
S = Studio(var)
jobs.start(S, pid, 'review', 'review', f'review {label}', 7, review.run, {'render_id': rid, 'profile': S.profile('timekeeper'),
           'other_profiles': [S.profile('diabetes-history')], 'research': S.research(pid), 'label': label}, sync=True)
st = S.state(pid); rv = st['review']['runs'][-1]
for f in [f for f in st['review']['findings'].values() if f['run'] == rv['id']]:
    print(f"{f['code']:<22} {f['scene']!s:<6} t={f['t']!s:<7} {f['severity']:<8} {f['detail'][:110]}")
