"""Local dashboard server (standard library only; no framework, no microservices).

    python -m director.dashboard.serve [--port 8765]

Routes:
  GET  /                  the dashboard app with a fresh snapshot
  GET  /api/snapshot      the snapshot as JSON (rebuilt from the components on every call)
  GET  /media/<path>      dashboard media (read-only, inside var/dashboard/media only)
  POST /api/decision      {item, decision, note}: appends one review_decided event. The ONLY write.
Anything else is 404/405. No route reaches the paid gateway or any provider; this module does not import them.
Approved items are locked: the only decision accepted after 'approved' is 'changes_requested' (which opens a new
revision instead of overwriting the approval).
"""
from __future__ import annotations
import argparse, json, mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from ..events import EventLog
from . import build as B

DECISIONS = {'approved', 'rejected', 'changes_requested', 'selected', 'accepted', 'dismissed', 'needs_source',
             'article_heard', 'article_missing', 'unsure'}


def decide(log: EventLog, item: str, decision: str, note: str = '', actor='owner (local dashboard)') -> dict:
    """Record one decision. Shared by the server and the Artifact ingest so both enforce the same rules."""
    if decision not in DECISIONS:
        raise ValueError(f'unknown decision {decision!r}')
    if not item or len(item) > 120:
        raise ValueError('bad item id')
    prev = [r for r in log.rows(kind='review_decided') if r['data'].get('item') == item]
    if prev and prev[-1]['status'] == 'approved' and decision != 'changes_requested':
        raise PermissionError('approved items are locked; request changes to open a new revision')
    project, video, scene = B.locate(item)
    log.emit('review_decided', project, video=video, scene=scene, status=decision, actor=actor, item=item, note=note[:2000])
    return {'item': item, 'decision': decision}


def ingest_rows(log: EventLog, rows: dict) -> dict:
    """Decisions saved on the Artifact copy ({doc_id: row}, oldest first) go through the same rules as the local app.
    Rows already in the log (same item, decision and time) are skipped; a refused row is reported, never forced."""
    seen = {(r['data'].get('item'), r['status'], r['data'].get('page_at')) for r in log.rows(kind='review_decided')}
    out = {'added': 0, 'skipped': 0, 'refused': []}
    for _, r in sorted(rows.items(), key=lambda kv: kv[1].get('at', '')):
        key = (r.get('item'), r.get('decision'), r.get('at'))
        if key in seen:
            out['skipped'] += 1; continue
        try:
            prev = [x for x in log.rows(kind='review_decided') if x['data'].get('item') == r.get('item')]
            if prev and prev[-1]['status'] == 'approved' and r.get('decision') != 'changes_requested':
                raise PermissionError('approved items are locked')
            if r.get('decision') not in DECISIONS:
                raise ValueError(f"unknown decision {r.get('decision')!r}")
            project, video, scene = B.locate(r.get('item', ''))
            log.emit('review_decided', project, video=video, scene=scene, status=r['decision'], actor='owner (dashboard page)',
                     item=r['item'], note=(r.get('note') or '')[:2000], page_at=r.get('at'))
            out['added'] += 1
        except (PermissionError, ValueError) as e:
            out['refused'].append({'item': r.get('item'), 'decision': r.get('decision'), 'why': str(e)})
    return out


class Handler(BaseHTTPRequestHandler):
    server_version = 'VideoDirectorDashboard/0.1'

    def _send(self, code, body: bytes, ctype='application/json; charset=utf-8'):
        self.send_response(code); self.send_header('Content-Type', ctype); self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store'); self.end_headers(); self.wfile.write(body)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode())

    def log_message(self, *a):          # quiet
        pass

    def do_GET(self):
        path = self.path.split('?', 1)[0]
        if path == '/':
            return self._send(200, B.render_app(B.snapshot(), mode='local').encode(), 'text/html; charset=utf-8')
        if path == '/api/snapshot':
            return self._json(200, B.snapshot())
        if path.startswith('/media/'):
            root = B.MEDIA.resolve()
            f = (root / path[len('/media/'):]).resolve()
            if root not in f.parents or not f.is_file():
                return self._json(404, {'error': 'not found'})
            return self._send(200, f.read_bytes(), mimetypes.guess_type(f.name)[0] or 'application/octet-stream')
        return self._json(404, {'error': 'not found'})

    def do_POST(self):
        if self.path != '/api/decision':
            return self._json(405, {'error': 'the dashboard only records decisions'})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get('Content-Length') or 0)) or b'{}')
            out = decide(B.log(), body.get('item', ''), body.get('decision', ''), body.get('note', ''))
            return self._json(200, out)
        except PermissionError as e:
            return self._json(409, {'error': str(e)})
        except (ValueError, KeyError, json.JSONDecodeError) as e:
            return self._json(400, {'error': str(e)})

    do_PUT = do_DELETE = do_PATCH = lambda self: self._json(405, {'error': 'not allowed'})


def make_server(port=8765, host='127.0.0.1'):
    return ThreadingHTTPServer((host, port), Handler)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--port', type=int, default=8765); a = ap.parse_args()
    B.prepare()
    print(f'Video Director dashboard on http://127.0.0.1:{a.port}  (local only; no paid actions)')
    make_server(a.port).serve_forever()
