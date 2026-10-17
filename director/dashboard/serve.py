"""Local dashboard server (standard library only; no framework, no microservices).

    python -m director.dashboard.serve [--port 8765]

Routes:
  GET  /                  → /studio (the guided Co-Pilot Studio is the primary interface)
  GET  /studio            the Co-Pilot Studio (director/copilot): idea → approvals → reviewed draft film
  GET  /api/copilot[/<id>] Co-Pilot projects / one project's guided view
  POST /api/copilot       one owner action (director/copilot/api.handle); the Co-Pilot carries on by itself after it
  GET  /studio/classic    the classic Studio, step by step (advanced)
  GET  /dashboard         the review dashboard app with a fresh snapshot (advanced)
  GET  /api/snapshot      the snapshot as JSON (rebuilt from the components on every call)
  GET  /media/<path>      dashboard media, with byte ranges (iPhone Safari will not play audio or video without them)
  POST /api/decision      one decision; the ONLY write. Same rules as the Artifact sync (sync._one), so a decision
                          made here and one carried over from the page are judged identically.
  GET  /api/studio[/<id>]  studio projects / one project's state and progress
  GET  /files/<id>/<path>  a studio project's files (read-only blobs), with byte ranges
  POST /api/studio        one studio action (director/studio/api.handle); long work runs as tracked jobs
Anything else is 404/405. No route reaches the paid gateway or any provider; this module does not import them.

Access from a phone (P7): `--lan` listens on the local network ONLY with an access code (VD_ACCESS_CODE, or one made at
start and printed once). Then every route, media included, needs the session cookie the code gives (POST /login);
a wrong code is slowed down and locked after 10 tries. Without --lan the server listens on 127.0.0.1 only.
"""
from __future__ import annotations
import argparse, hashlib, hmac, json, mimetypes, os, re, secrets, time, uuid
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ..events import EventLog
from . import build as B

DECISIONS = {'approved', 'rejected', 'changes_requested', 'selected', 'concept_selected', 'accepted', 'dismissed',
             'needs_source', 'article_heard', 'article_missing', 'heard_english', 'heard_other', 'unsure', 'playback_failed',
             'flagged'}
STUDIO_PAGE = Path(__file__).resolve().parents[1] / 'studio' / 'studio.html'
COPILOT_PAGE = Path(__file__).resolve().parents[1] / 'copilot' / 'copilot.html'
MAX_BODY = 18 * 1024 * 1024
HTTP = {'recorded': 200, 'duplicate': 200, 'conflict': 409, 'refused': 422, 'failed': 400}


def decide(log: EventLog, item: str, decision: str, note: str = '', playback=None, decision_id=None, at=None) -> dict:
    """Record one decision made in the local app. Returns the receipt (status recorded/duplicate/conflict/...)."""
    from . import sync
    from .events_time import now
    doc = {'decision_id': decision_id or 'local-' + uuid.uuid4().hex[:16], 'item': item, 'decision': decision,
           'note': note or '', 'playback': playback, 'at': at or now()}
    return sync._one(log, doc, 'local app', {i['id']: i for i in B.snapshot()['inbox_checks']})


# ------------------------------------------------------------------ access code (off unless a code is set)
ACCESS = {'code': None}
FAILS: dict = {}                                                  # ip → [count, first failure time]
LOGIN_PAGE = '''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>مخرج الفيديو</title><style>body{font:17px/1.6 system-ui,sans-serif;background:#f2f3f5;color:#14171b;margin:0;display:flex;min-height:100vh;align-items:center;justify-content:center;padding:16px}
form{background:#fff;border:1px solid #d6dae0;border-radius:16px;padding:20px;display:flex;flex-direction:column;gap:12px;width:100%;max-width:360px}
input,button{font:inherit;border-radius:12px;padding:12px;border:1px solid #d6dae0;min-height:48px}button{background:#2b5b87;color:#fff;border-color:#2b5b87;font-weight:600}
@media (prefers-color-scheme:dark){body{background:#0f1114;color:#e8eaed}form{background:#16191e;border-color:#2a2f37}input{background:#0b0d10;color:#e8eaed;border-color:#2a2f37}}</style></head>
<body><form method="post" action="/login"><b>مخرج الفيديو</b><label>رمز الدخول<input name="code" type="password" autocomplete="current-password" required autofocus></label>
<button>ادخل</button>{msg}</form></body></html>'''


def _form_value(x):                                              # one value of a posted form (this module imports no network library)
    x = x.replace('+', ' ')
    return re.sub(rb'%([0-9A-Fa-f]{2})', lambda m: bytes([int(m.group(1), 16)]), x.encode('ascii', 'replace')).decode('utf-8', 'replace')


def _session(code):
    return hmac.new(code.encode(), b'vd-session-1', hashlib.sha256).hexdigest()


class Handler(BaseHTTPRequestHandler):
    server_version = 'VideoDirectorDashboard/0.2'

    def _authorized(self):
        code = ACCESS['code']
        if not code: return True
        for part in (self.headers.get('Cookie') or '').split(';'):
            k, _, v = part.strip().partition('=')
            if k == 'vd_auth' and hmac.compare_digest(v, _session(code)): return True
        return False

    def _same_origin(self):                                       # a write must come from this app's own page
        o = self.headers.get('Origin')
        return not o or o.split('://', 1)[-1] == (self.headers.get('Host') or '')

    def _login(self):
        ip, now = self.client_address[0], time.time()
        n, t0 = FAILS.get(ip, [0, now])
        if now - t0 > 600: n, t0 = 0, now
        if n >= 10:
            return self._send(429, LOGIN_PAGE.replace('{msg}', '<p>محاولات كثيرة. حاول بعد 10 دقائق.</p>').encode(), 'text/html; charset=utf-8')
        body = self.rfile.read(min(int(self.headers.get('Content-Length') or 0), 4096)).decode('ascii', 'replace')
        got = next((_form_value(kv.split('=', 1)[1]) for kv in body.split('&') if kv.startswith('code=')), '')
        if ACCESS['code'] and hmac.compare_digest(got.encode(), ACCESS['code'].encode()):
            FAILS.pop(ip, None)
            return self._send(303, b'', 'text/plain', {'Location': '/studio',
                              'Set-Cookie': f'vd_auth={_session(ACCESS["code"])}; HttpOnly; SameSite=Strict; Path=/; Max-Age=2592000'})
        FAILS[ip] = [n + 1, t0]; time.sleep(1)
        return self._send(401, LOGIN_PAGE.replace('{msg}', '<p>الرمز غير صحيح.</p>').encode(), 'text/html; charset=utf-8')

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
        if not self._authorized():
            if path.startswith(('/api/', '/media/', '/files/')): return self._json(401, {'error': 'sign in first'})
            return self._send(200, LOGIN_PAGE.replace('{msg}', '').encode(), 'text/html; charset=utf-8')
        if path == '/':
            return self._send(302, b'', 'text/plain', {'Location': '/studio'})
        if path in ('/dashboard', '/api/snapshot') and not B.has_archive():        # a new computer: the archive is not there
            if path == '/api/snapshot': return self._json(404, {'error': 'no archive on this computer'})
            return self._send(200, LOGIN_PAGE.replace('<form method="post" action="/login"><b>مخرج الفيديو</b><label>رمز الدخول<input name="code" type="password" autocomplete="current-password" required autofocus></label>\n<button>ادخل</button>{msg}</form>',
                              '<form><b>لوحة التقارير</b><p>الأرشيف (الحلقات القديمة) غير موجود على هذا الجهاز. الاستوديو يعمل بدونه.</p><a href="/studio">افتح الاستوديو</a></form>').encode(), 'text/html; charset=utf-8')
        if path == '/dashboard':
            return self._send(200, B.render_app(B.snapshot(), mode='local').encode(), 'text/html; charset=utf-8')
        if path == '/api/snapshot':
            return self._json(200, B.snapshot())
        if path == '/studio':
            return self._send(200, COPILOT_PAGE.read_bytes(), 'text/html; charset=utf-8')
        if path == '/studio/classic':
            return self._send(200, STUDIO_PAGE.read_bytes(), 'text/html; charset=utf-8')
        if path == '/api/copilot':
            from ..copilot import api as CA
            return self._json(200, {'projects': CA.projects(B.VAR)})
        if path.startswith('/api/copilot/'):
            from ..copilot import api as CA
            from ..studio.store import Refused
            try:
                return self._json(200, CA.view(B.VAR, path.split('/')[3]))
            except Refused as e:
                return self._json(404, {'error': str(e)})
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
        """Byte ranges read from disk (only the part asked for: a film is tens of MB and a player asks many small ranges)."""
        ctype = mimetypes.guess_type(f.name)[0] or 'application/octet-stream'
        n = f.stat().st_size
        rng = re.fullmatch(r'bytes=(\d*)-(\d*)', (self.headers.get('Range') or '').strip())
        if not rng:
            return self._send(200, f.read_bytes(), ctype, {'Accept-Ranges': 'bytes'})
        a, b = rng.groups()
        start, end = (int(a), int(b) if b else n - 1) if a else (max(0, n - int(b or 0)), n - 1)
        if start >= n or start > end:
            return self._send(416, b'', ctype, {'Content-Range': f'bytes */{n}', 'Accept-Ranges': 'bytes'})
        end = min(end, n - 1, start + 8 * 1024 * 1024 - 1)                  # at most 8 MB per answer; the player asks again
        with open(f, 'rb') as fh:
            fh.seek(start); data = fh.read(end - start + 1)
        return self._send(206, data, ctype, {'Content-Range': f'bytes {start}-{end}/{n}', 'Accept-Ranges': 'bytes'})

    def do_POST(self):
        if self.path == '/login': return self._login()
        if not self._authorized(): return self._json(401, {'error': 'sign in first'})
        if not self._same_origin(): return self._json(403, {'error': 'this request did not come from the app'})
        if self.path == '/api/copilot/_test':                    # failure injection for the browser scenarios, test mode only
            if os.environ.get('VD_STUDIO_TEST') != '1': return self._json(403, {'error': 'test hooks are off'})
            from ..copilot import ai as CAI
            from ..studio import jobs as SJ
            body = json.loads(self.rfile.read(int(self.headers.get('Content-Length') or 0)) or b'{}')
            if body.get('ai_probe'):                              # try one AI call through the real locks (refused or not)
                from ..copilot import api as CA
                pr = body['ai_probe']
                try:
                    CAI.call(CA.studio(B.VAR), pr['project'], pr.get('kind', 'fact_check'), {'lines': [], 'research': {'claims': []}})
                    return self._json(200, {'ok': True, 'refused': None})
                except (CAI.AIRefused, CAI.AIFailed) as e:
                    return self._json(200, {'ok': True, 'refused': str(e)})
            CAI.MOCK_INJECT.clear(); CAI.MOCK_INJECT.update(body.get('inject') or {})
            SJ.FAIL_NEXT.update(body.get('fail_next') or {})
            return self._json(200, {'ok': True, 'inject': CAI.MOCK_INJECT})
        if self.path == '/api/copilot':
            from ..copilot import api as CA
            n = int(self.headers.get('Content-Length') or 0)
            if n > MAX_BODY: return self._json(413, {'status': 'refused', 'reason': 'too large'})
            try:
                body = json.loads(self.rfile.read(n) or b'{}')
            except json.JSONDecodeError as e:
                return self._json(400, {'status': 'failed', 'reason': str(e)})
            try:
                code, r = CA.handle(B.VAR, body)
            except Exception as e:
                return self._json(500, {'status': 'failed', 'reason': f'not recorded ({type(e).__name__}: {e})'})
            return self._json(code, r)
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
    ap = argparse.ArgumentParser(); ap.add_argument('--port', type=int, default=8765)
    ap.add_argument('--lan', action='store_true', help='listen on the local network (an access code is then required)')
    a = ap.parse_args()
    ACCESS['code'] = os.environ.get('VD_ACCESS_CODE') or (secrets.token_urlsafe(8) if a.lan else None)
    if ACCESS['code'] and len(ACCESS['code']) < 8: raise SystemExit('VD_ACCESS_CODE must be at least 8 characters')
    B.prepare()
    if a.lan:
        print(f'Video Director on the local network, port {a.port}. Access code: '
              + (ACCESS['code'] if not os.environ.get('VD_ACCESS_CODE') else '(the one in VD_ACCESS_CODE)'))
    else:
        print(f'Video Director on http://127.0.0.1:{a.port}/studio  (local only; no paid actions)')
    from director.copilot import orchestrator as _O
    from director.studio import api as _SA
    print('Co-Pilot projects resumed:', _O.resume_all(_SA.studio(B.VAR)))
    import signal

    def _stop(signum, frame):                                   # a stopped server leaves no renderer running behind it
        from director.studio.engine import kill_orphans
        kill_orphans(B.VAR / 'studio')
        raise SystemExit(0)
    signal.signal(signal.SIGTERM, _stop)
    make_server(a.port, '0.0.0.0' if a.lan else '127.0.0.1').serve_forever()
