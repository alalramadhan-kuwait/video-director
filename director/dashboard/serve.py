"""Local dashboard server (standard library only; no framework, no microservices).

    python -m director.dashboard.serve [--port 8765]

Routes:
  GET  /                  the dashboard app with a fresh snapshot
  GET  /api/snapshot      the snapshot as JSON (rebuilt from the components on every call)
  GET  /media/<path>      dashboard media, with byte ranges (iPhone Safari will not play audio or video without them)
  POST /api/decision      one decision; the ONLY write. Same rules as the Artifact sync (sync._one), so a decision
                          made here and one carried over from the page are judged identically.
  GET  /studio            the Studio: new video projects (director/studio)
  GET  /api/studio[/<id>]  studio projects / one project's state and progress
  GET  /files/<id>/<path>  a studio project's files (read-only blobs), with byte ranges
  POST /api/studio        one studio action (director/studio/api.handle); long work runs as tracked jobs
Anything else is 404/405. No route reaches the paid gateway or any provider; this module does not import them.
"""
from __future__ import annotations
import argparse, json, mimetypes, os, re, uuid
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ..events import EventLog
from . import build as B

DECISIONS = {'approved', 'rejected', 'changes_requested', 'selected', 'concept_selected', 'accepted', 'dismissed',
             'needs_source', 'article_heard', 'article_missing', 'heard_english', 'heard_other', 'unsure', 'playback_failed',
             'flagged'}
STUDIO_PAGE = Path(__file__).resolve().parents[1] / 'studio' / 'studio.html'
HTTP = {'recorded': 200, 'duplicate': 200, 'conflict': 409, 'refused': 422, 'failed': 400}


def decide(log: EventLog, item: str, decision: str, note: str = '', playback=None, decision_id=None, at=None) -> dict:
    """Record one decision made in the local app. Returns the receipt (status recorded/duplicate/conflict/...)."""
    from . import sync
    from .events_time import now
    doc = {'decision_id': decision_id or 'local-' + uuid.uuid4().hex[:16], 'item': item, 'decision': decision,
           'note': note or '', 'playback': playback, 'at': at or now()}
    return sync._one(log, doc, 'local app', {i['id']: i for i in B.snapshot()['inbox_checks']})


class Handler(BaseHTTPRequestHandler):
    server_version = 'VideoDirectorDashboard/0.2'

    def _send(self, code, body: bytes, ctype='application/json; charset=utf-8', extra=None):
        self.send_response(code); self.send_header('Content-Type', ctype); self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != 'HEAD':
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):   # the browser cancelled a media range it no longer needs
                pass

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
        if path == '/studio':
            return self._send(200, STUDIO_PAGE.read_bytes(), 'text/html; charset=utf-8')
        if path == '/api/studio':
            from ..studio import api as SA
            return self._json(200, {'projects': SA.studio(B.VAR).projects()})
        if path.startswith('/api/studio/'):
            from ..studio import api as SA
            from ..studio.store import Refused
            try:
                return self._json(200, SA.view(B.VAR, path.split('/')[3]))
            except Refused as e:
                return self._json(404, {'error': str(e)})
        if path.startswith('/files/'):
            parts = path.split('/', 3)
            if len(parts) < 4: return self._json(404, {'error': 'not found'})
            root = (B.VAR / 'studio' / parts[2] / 'blobs').resolve()
            f = (B.VAR / 'studio' / parts[2] / parts[3]).resolve()
            if root not in f.parents or not f.is_file():
                return self._json(404, {'error': 'not found'})
            return self._media(f)
        if path.startswith('/media/'):
            root = B.MEDIA.resolve()
            f = (root / path[len('/media/'):]).resolve()
            if root not in f.parents or not f.is_file():
                return self._json(404, {'error': 'not found'})
            return self._media(f)
        return self._json(404, {'error': 'not found'})

    do_HEAD = do_GET

    def _media(self, f):
        data, ctype = f.read_bytes(), mimetypes.guess_type(f.name)[0] or 'application/octet-stream'
        rng = re.fullmatch(r'bytes=(\d*)-(\d*)', (self.headers.get('Range') or '').strip())
        if not rng:
            return self._send(200, data, ctype, {'Accept-Ranges': 'bytes'})
        a, b = rng.groups(); n = len(data)
        start, end = (int(a), int(b) if b else n - 1) if a else (max(0, n - int(b or 0)), n - 1)
        if start >= n or start > end:
            return self._send(416, b'', ctype, {'Content-Range': f'bytes */{n}', 'Accept-Ranges': 'bytes'})
        end = min(end, n - 1)
        return self._send(206, data[start:end + 1], ctype, {'Content-Range': f'bytes {start}-{end}/{n}', 'Accept-Ranges': 'bytes'})

    def do_POST(self):
        if self.path in ('/api/studio', '/api/studio/_test'):
            from ..studio import api as SA, jobs as SJ
            try:
                body = json.loads(self.rfile.read(int(self.headers.get('Content-Length') or 0)) or b'{}')
            except json.JSONDecodeError as e:
                return self._json(400, {'status': 'failed', 'reason': str(e)})
            if self.path == '/api/studio/_test':                # failure injection, only when the test flag is set
                if os.environ.get('VD_STUDIO_TEST') != '1': return self._json(403, {'error': 'test hooks are off'})
                SJ.FAIL_NEXT.update(body.get('fail_next') or {}); return self._json(200, {'ok': True, 'fail_next': SJ.FAIL_NEXT})
            try:
                code, r = SA.handle(B.VAR, body)
            except Exception as e:
                return self._json(500, {'status': 'failed', 'reason': f'not recorded ({type(e).__name__}: {e})'})
            return self._json(code, r)
        if self.path != '/api/decision':
            return self._json(405, {'error': 'the dashboard only records decisions'})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get('Content-Length') or 0)) or b'{}')
        except json.JSONDecodeError as e:
            return self._json(400, {'status': 'failed', 'reason': str(e)})
        try:
            r = decide(B.log(), body.get('item', ''), body.get('decision', ''), body.get('note', ''), body.get('playback'),
                       body.get('decision_id'), body.get('at'))
        except Exception as e:                       # never leave the page without an answer: nothing was recorded
            return self._json(500, {'status': 'failed', 'reason': f'not recorded ({type(e).__name__}: {e})'})
        return self._json(HTTP[r['status']], r)

    do_PUT = do_DELETE = do_PATCH = lambda self: self._json(405, {'error': 'not allowed'})


def make_server(port=8765, host='127.0.0.1'):
    return ThreadingHTTPServer((host, port), Handler)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--port', type=int, default=8765); a = ap.parse_args()
    B.prepare()
    print(f'Video Director dashboard on http://127.0.0.1:{a.port}  (local only; no paid actions)')
    import signal

    def _stop(signum, frame):                                   # a stopped server leaves no renderer running behind it
        from director.studio.engine import kill_orphans
        kill_orphans(B.VAR / 'studio')
        raise SystemExit(0)
    signal.signal(signal.SIGTERM, _stop)
    make_server(a.port).serve_forever()
