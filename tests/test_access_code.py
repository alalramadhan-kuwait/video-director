"""P7: with an access code set (phone access on the local network), nothing is served or changed without signing in."""
from tests import _guard  # noqa: F401
import io, unittest
from director.dashboard import serve as SV


class TestAccessCode(unittest.TestCase):
    def setUp(self):
        SV.ACCESS['code'] = 'correct-horse-9'; SV.FAILS.clear()

    def tearDown(self):
        SV.ACCESS['code'] = None; SV.FAILS.clear()

    def req(self, path, data=None, cookie=None, ctype='application/json', origin=None):
        """One request straight through the server's handler (no socket: the tests have no network)."""
        h = object.__new__(SV.Handler)
        raw = data or b''
        h.rfile, h.wfile = io.BytesIO(raw), io.BytesIO()
        h.headers = {'Content-Length': str(len(raw)), 'Host': 'phone.local:8765', **({'Cookie': cookie} if cookie else {}),
                     **({'Content-Type': ctype} if data is not None else {}), **({'Origin': origin} if origin else {})}
        method = 'POST' if data is not None else 'GET'
        h.path, h.command, h.request_version, h.requestline = path, method, 'HTTP/1.1', f'{method} {path} HTTP/1.1'
        h.client_address, h.close_connection = ('127.0.0.1', 0), True
        getattr(h, 'do_' + method)()
        out = h.wfile.getvalue()
        head, body = out.split(b'\r\n\r\n', 1)
        hd = dict(l.split(': ', 1) for l in head.decode('latin-1').split('\r\n')[1:])
        return int(out.split(b' ', 2)[1]), hd, body

    def test_everything_needs_the_code(self):
        for path in ('/api/copilot', '/api/studio', '/media/x.jpg', '/files/p/x', '/api/snapshot'):
            self.assertEqual(self.req(path)[0], 401, path)
        code, _, body = self.req('/studio')
        self.assertEqual(code, 200); self.assertIn('رمز الدخول'.encode(), body); self.assertNotIn(b'cp_gate', body)   # the sign-in page, not the app
        self.assertEqual(self.req('/api/copilot', b'{"action":"cp_mode","args":{"mode":"manual"}}')[0], 401)
        self.assertEqual(self.req('/studio', cookie='vd_auth=forged')[0:1], (200,))
        self.assertIn('رمز الدخول'.encode(), self.req('/studio', cookie='vd_auth=forged')[2])

    def test_sign_in_then_only_same_origin_writes(self):
        code, h, _ = self.req('/login', b'code=wrong-code', ctype='application/x-www-form-urlencoded')
        self.assertEqual(code, 401)
        code, h, _ = self.req('/login', b'code=correct-horse-9', ctype='application/x-www-form-urlencoded')
        self.assertEqual(code, 303)
        ck = h['Set-Cookie']; self.assertIn('HttpOnly', ck); self.assertIn('SameSite=Strict', ck)
        cookie = ck.split(';')[0]
        self.assertEqual(self.req('/api/copilot', cookie=cookie)[0], 200)
        self.assertEqual(self.req('/api/copilot', b'{}', cookie=cookie, origin='http://evil.example')[0], 403)
        self.assertNotEqual(self.req('/api/copilot', b'{}', cookie=cookie, origin='http://phone.local:8765')[0], 403)

    def test_guessing_is_locked(self):
        for _ in range(10): SV.FAILS.setdefault('127.0.0.1', [0, __import__('time').time()])[0] += 1
        self.assertEqual(self.req('/login', b'code=correct-horse-9', ctype='application/x-www-form-urlencoded')[0], 429)

    def test_off_without_a_code(self):
        SV.ACCESS['code'] = None
        self.assertEqual(self.req('/api/copilot')[0], 200)

    def test_form_value(self):
        self.assertEqual(SV._form_value('a%20b+c%D8%B1'), 'a b cر')
