"""Background work for the studio: one thread per job, tracked as a task with counted units and measured times.

A job writes 'job' events (running → finished / failed). If the server stops while a job runs, the job has no
finished event and no live thread, so the project shows it as INTERRUPTED with a Resume button; resuming runs the
same job again. Voice lines and art stills that already finished are reused (content-addressed); a RENDER starts again
from its first frame (frames are not kept between runs), and the renderer left behind by the old server is stopped.
"""
from __future__ import annotations
import threading, time, traceback, uuid

FAIL_NEXT: dict[str, str] = {}        # test hook: {job kind: message} makes the next job of that kind fail on purpose


def start(studio, pid, kind, stage, what, total, fn, args=None, sync=False, request_id=None):
    """Run fn(studio, pid, task, **args) as a tracked job. Returns the job id."""
    # Reserve the job and record its receipt under the same lock as Studio.act.
    # Otherwise simultaneous HTTP requests can both observe no running job.
    with studio.lock:
        if request_id:
            for event in studio.events(pid):
                if event['data'].get('request_id') == request_id:
                    if event['status'] == 'job':
                        return event['data']['args']['id']
                    from .store import Refused
                    raise Refused('request id already used by another action')
        jid = f'j-{kind}-{uuid.uuid4().hex[:8]}'
        if any(j['kind'] == kind and j['state'] == 'running' for j in studio.state(pid)['jobs']):
            from .store import Refused
            raise Refused(f'{what} is already running')
        studio.jobs[jid] = {'pid': pid, 'kind': kind, 'started': time.time()}
        try:
            shown = {k: (f'<{getattr(v, "__name__", "callable")}>' if callable(v) else v) for k, v in (args or {}).items()}
            studio.act(pid, 'job', {'id': jid, 'kind': kind, 'stage': stage, 'what': what, 'state': 'running', 'args': shown},
                       actor='system', request_id=request_id)
        except Exception:
            studio.jobs.pop(jid, None)
            raise

    def body():
        t0 = time.monotonic()
        try:
            with studio.log.task(pid, what, total, stage=stage, actor='system') as task:
                if kind in FAIL_NEXT:
                    raise RuntimeError(FAIL_NEXT.pop(kind))
                out = fn(studio, pid, task, **(args or {})) or {}
            studio.act(pid, 'job', {'id': jid, 'kind': kind, 'stage': stage, 'what': what, 'state': 'finished',
                                    'seconds': round(time.monotonic() - t0, 2), 'out': out, 'run': task.id}, actor='system')
        except Exception as e:
            studio.act(pid, 'job', {'id': jid, 'kind': kind, 'stage': stage, 'what': what, 'state': 'failed',
                                    'seconds': round(time.monotonic() - t0, 2), 'error': f'{type(e).__name__}: {e}',
                                    'trace': traceback.format_exc()[-1500:]}, actor='system')
        finally:
            studio.jobs.pop(jid, None)

    if sync:
        body()
    else:
        threading.Thread(target=body, name=jid, daemon=True).start()
    return jid
