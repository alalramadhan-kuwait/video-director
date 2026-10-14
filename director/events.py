"""Structured production events: the only source the dashboard uses for progress, times and history.

* Append-only SQLite table; UPDATE and DELETE are refused by triggers.
* Progress is never a guess: a task declares how many units it has (lines, scenes, clips) and records each unit
  as it finishes. Completion = units done / units total, shown as both numbers.
* Elapsed time is measured (monotonic clock inside a run, wall-clock timestamps on every event).
* An ETA is given only when it is reliable: at least MIN_UNITS finished units in this run, and their durations
  vary little (coefficient of variation <= MAX_CV). Otherwise the dashboard is told why there is no ETA.
* History that happened before this log existed can be imported with source='reconstructed' and the evidence it
  comes from (file times, git commits, provider history). It is never shown as live tracking.
"""
from __future__ import annotations
import json, sqlite3, statistics, time
from contextlib import contextmanager
from pathlib import Path

MIN_UNITS = 3
MAX_CV = 0.6
KINDS = {'task_started', 'unit_done', 'task_finished', 'task_failed', 'blocked', 'unblocked',
         'stage_status', 'review_requested', 'review_decided', 'revision', 'note', 'sync', 'studio'}
STAGE_STATUS = ('not_started', 'processing', 'waiting_review', 'approved', 'blocked', 'failed', 'unknown')
SOURCES = ('live', 'reconstructed')

SCHEMA = """
CREATE TABLE IF NOT EXISTS events(
  seq INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, kind TEXT NOT NULL, project TEXT NOT NULL,
  video TEXT, scene TEXT, stage TEXT, task TEXT, status TEXT, units_done INTEGER, units_total INTEGER,
  duration_s REAL, source TEXT NOT NULL, actor TEXT NOT NULL, evidence TEXT, data TEXT);
CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
"""


def now_iso():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


class EventLog:
    def __init__(self, path):
        self.path = Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._db() as db:
            db.executescript(SCHEMA)

    def _db(self):
        db = sqlite3.connect(self.path); db.row_factory = sqlite3.Row
        return _Closing(db)

    def emit(self, kind, project, *, video=None, scene=None, stage=None, task=None, status=None, units_done=None,
             units_total=None, duration_s=None, source='live', actor='system', evidence=None, at=None, **data):
        if kind not in KINDS: raise ValueError(f'unknown event kind {kind}')
        if source not in SOURCES: raise ValueError(f'unknown source {source}')
        if kind == 'stage_status' and status not in STAGE_STATUS: raise ValueError(f'bad stage status {status}')
        if source == 'reconstructed' and not evidence: raise ValueError('a reconstructed event must name its evidence')
        row = (at or now_iso(), kind, project, video, scene, stage, task, status, units_done, units_total, duration_s,
               source, actor, evidence, json.dumps(data, ensure_ascii=False) if data else None)
        with self._db() as db:
            cur = db.execute('INSERT INTO events(at,kind,project,video,scene,stage,task,status,units_done,units_total,'
                             'duration_s,source,actor,evidence,data) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', row)
            db.commit()
            return cur.lastrowid

    def rows(self, **where):
        q, args = 'SELECT * FROM events', []
        if where:
            q += ' WHERE ' + ' AND '.join(f'{k} IS ?' if v is None else f'{k} = ?' for k, v in where.items())
            args = list(where.values())
        with self._db() as db:
            out = [dict(r) for r in db.execute(q + ' ORDER BY seq', args)]
        for r in out:
            r['data'] = json.loads(r['data']) if r['data'] else {}
        return out

    # ------------------------------------------------------------------ tasks
    @contextmanager
    def task(self, project, task, total, *, video=None, stage=None, actor='system'):
        """Track one run of a task with a known number of units. Usage:
            with log.task('diabetes-history', 'evidence pack', 20, video='ep7') as t:
                for s in scenes: ...; t.unit(scene=s)"""
        run = _Run(self, project, task, total, video, stage, actor)
        self.emit('task_started', project, video=video, stage=stage, task=task, units_done=0, units_total=total,
                  actor=actor, run=run.id)
        try:
            yield run
        except Exception as e:
            self.emit('task_failed', project, video=video, stage=stage, task=task, units_done=run.done, units_total=total,
                      duration_s=round(time.monotonic() - run.t0, 3), actor=actor, run=run.id, error=f'{type(e).__name__}: {e}')
            raise
        self.emit('task_finished', project, video=video, stage=stage, task=task, units_done=run.done, units_total=total,
                  duration_s=round(time.monotonic() - run.t0, 3), actor=actor, run=run.id)

    def task_summary(self, run_id):
        evs = [r for r in self.rows() if r['data'].get('run') == run_id]
        return summarize(evs)

    def runs(self, project=None):
        ids = []
        for r in self.rows(**({'project': project} if project else {})):
            if r['kind'] == 'task_started' and r['data'].get('run') not in ids:
                ids.append(r['data']['run'])
        return [self.task_summary(i) for i in ids]


class _Run:
    def __init__(self, log, project, task, total, video, stage, actor):
        self.log, self.project, self.task, self.total, self.video, self.stage, self.actor = log, project, task, total, video, stage, actor
        self.id = f'run_{time.time_ns():x}'
        self.t0 = self.t_last = time.monotonic(); self.done = 0; self.durs = []

    def unit(self, scene=None, **data):
        t = time.monotonic(); dur = round(t - self.t_last, 3); self.t_last = t; self.done += 1; self.durs.append(dur)
        e = eta(self.durs, self.total - self.done)          # what the dashboard would have shown at this moment
        self.log.emit('unit_done', self.project, video=self.video, scene=scene, stage=self.stage, task=self.task,
                      units_done=self.done, units_total=self.total, duration_s=dur, actor=self.actor, run=self.id,
                      eta_s=e['eta_s'], eta_reason=e['eta_reason'], **data)


def summarize(evs: list[dict]) -> dict:
    """Progress, elapsed time and (only if reliable) ETA for one run, from its events alone."""
    if not evs:
        return {}
    start = next(e for e in evs if e['kind'] == 'task_started')
    end = next((e for e in evs if e['kind'] in ('task_finished', 'task_failed')), None)
    units = [e for e in evs if e['kind'] == 'unit_done']
    done, total = (units[-1]['units_done'] if units else 0), start['units_total']
    durs = [u['duration_s'] for u in units]
    out = {'run': start['data'].get('run'), 'project': start['project'], 'video': start['video'], 'stage': start['stage'],
           'task': start['task'], 'started': start['at'], 'finished': end['at'] if end else None,
           'state': 'finished' if end and end['kind'] == 'task_finished' else 'failed' if end else 'running',
           'units_done': done, 'units_total': total,
           'elapsed_s': end['duration_s'] if end else (round(sum(durs), 3) if durs else 0.0),
           'error': end['data'].get('error') if end and end['kind'] == 'task_failed' else None}
    out.update(eta(durs, total - done) if out['state'] == 'running' else {'eta_s': None, 'eta_reason': 'not running'})
    # how good the ETA was: the first reliable prediction against what actually happened
    first = next((u for u in units if u['data'].get('eta_s') not in (None, 0.0)), None)
    if first and out['state'] == 'finished':
        actual = round(sum(durs[units.index(first) + 1:]), 1)
        out['eta_check'] = {'after_units': first['units_done'], 'predicted_s': first['data']['eta_s'], 'actual_s': actual}
    return out


def eta(durations: list[float], remaining: int) -> dict:
    if remaining <= 0:
        return {'eta_s': 0.0, 'eta_reason': 'nothing left'}
    if len(durations) < MIN_UNITS:
        return {'eta_s': None, 'eta_reason': f'needs {MIN_UNITS} finished units, has {len(durations)}'}
    m = statistics.mean(durations)
    cv = statistics.pstdev(durations) / m if m > 0 else float('inf')
    if cv > MAX_CV:
        return {'eta_s': None, 'eta_reason': f'unit times vary too much (cv {cv:.2f} > {MAX_CV})'}
    return {'eta_s': round(m * remaining, 1), 'eta_reason': f'mean of {len(durations)} measured units × {remaining} left'}


class _Closing:
    def __init__(self, db): self.db = db
    def __enter__(self): return self.db
    def __exit__(self, *a): self.db.close()
