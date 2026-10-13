"""Dashboard: real progress only, append-only history, locked approvals, and no path to a paid provider."""
from tests import _guard  # noqa: F401
import io, json, re, shutil, sqlite3, tempfile, unittest
from pathlib import Path
from unittest import mock

from director import events as E
from director.events import EventLog
from director.dashboard import build as B, history, serve
from director.voice import gateway
from tests.fixtures import S, have_ro

ROOT = Path(__file__).resolve().parent.parent
READY = have_ro and (ROOT / 'var/review/ep7-final/artistic_report.json').exists() and (ROOT / 'var/pages/voice-royal-oak/data.json').exists() \
    and (ROOT / 'var/pages/directions/data.json').exists() and (ROOT / 'var/dashboard/media/ep7/clips').exists()


class TestEvents(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.log = EventLog(Path(self.tmp.name) / 'e.sqlite')

    def tearDown(self):
        self.tmp.cleanup()

    def test_append_only(self):
        self.log.emit('note', 'p', note='x')
        db = sqlite3.connect(self.log.path)
        for sql in ('UPDATE events SET kind="revision"', 'DELETE FROM events'):
            with self.assertRaises(sqlite3.DatabaseError):
                db.execute(sql)
        db.close()

    def test_reconstructed_needs_evidence_and_kinds_are_checked(self):
        with self.assertRaises(ValueError):
            self.log.emit('revision', 'p', source='reconstructed')
        with self.assertRaises(ValueError):
            self.log.emit('made_up', 'p')
        with self.assertRaises(ValueError):
            self.log.emit('stage_status', 'p', status='90%')

    def test_eta_only_when_reliable(self):
        self.assertIsNone(E.eta([1.0, 1.1], 5)['eta_s'])                      # too few units
        self.assertIsNone(E.eta([0.1, 3.0, 0.2, 5.0], 5)['eta_s'])            # too irregular
        self.assertAlmostEqual(E.eta([1.0, 1.0, 1.0], 4)['eta_s'], 4.0)

    def test_task_progress_is_counted_and_failures_recorded(self):
        import time
        with self.log.task('p', 'clips', 6, video='v') as t:
            for _ in range(6): time.sleep(0.02); t.unit()
        r = self.log.runs()[0]
        self.assertEqual((r['state'], r['units_done'], r['units_total']), ('finished', 6, 6))
        self.assertIn('eta_check', r)
        with self.assertRaises(RuntimeError):
            with self.log.task('p', 'boom', 3) as t:
                t.unit(); raise RuntimeError('ffmpeg died')
        f = self.log.runs()[1]
        self.assertEqual((f['state'], f['units_done']), ('failed', 1))
        self.assertIn('ffmpeg died', f['error'])


@unittest.skipUnless(READY, 'dashboard inputs not built (run python -m director.dashboard.build)')
class TestDashboard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); var = Path(self.tmp.name)
        shutil.copyfile(ROOT / 'var/dashboard/events.sqlite', var / 'events.sqlite')
        (var / 'media').symlink_to(ROOT / 'var/dashboard/media')
        self.p = [mock.patch.object(B, 'VAR', var), mock.patch.object(B, 'MEDIA', var / 'media')]
        for x in self.p: x.start()
        # any attempt to reach a paid provider fails the test
        self.paid = [mock.patch.object(gateway.PaidGateway, 'run', side_effect=AssertionError('paid gateway reached')),
                     mock.patch.object(gateway.ElevenLabsProvider, 'synthesize', side_effect=AssertionError('provider reached'))]
        for x in self.paid: x.start()

    def tearDown(self):
        for x in self.p + self.paid: x.stop()
        self.tmp.cleanup()

    def req(self, method, path, body=None):
        h = object.__new__(serve.Handler)
        raw = json.dumps(body).encode() if body is not None else b''
        h.rfile, h.wfile = io.BytesIO(raw), io.BytesIO()
        h.headers = {'Content-Length': str(len(raw))}
        h.path, h.command, h.request_version, h.requestline = path, method, 'HTTP/1.1', f'{method} {path} HTTP/1.1'
        h.client_address, h.close_connection = ('127.0.0.1', 0), True
        getattr(h, 'do_' + method)()
        out = h.wfile.getvalue()
        code = int(out.split(b' ', 2)[1])
        return code, out.split(b'\r\n\r\n', 1)[1]

    def test_snapshot_counts_are_real_units(self):
        s = B.snapshot()
        for p in s['projects'].values():
            for v in p['videos']:
                self.assertEqual([x['stage'] for x in v['stages']], ['script', 'hook', 'voice', 'art', 'render', 'final', 'publish'])
                for st in v['stages']:
                    self.assertIn(st['status'], E.STAGE_STATUS)
                    if st['units']:
                        self.assertIsInstance(st['units']['done'], int)
                        self.assertLessEqual(st['units']['done'], st['units']['total'])
        ep7 = s['projects']['diabetes-history']['videos'][0]
        art = next(x for x in ep7['stages'] if x['stage'] == 'art')
        self.assertEqual(art['units']['total'], sum(len(sc['findings']) for sc in ep7['scenes']))
        self.assertEqual(next(x for x in ep7['stages'] if x['stage'] == 'publish')['status'], 'blocked')
        self.assertEqual(len(s['projects']['timekeeper']['videos'][0]['scenes']), 36)

    def test_no_secrets_or_voice_ids_in_the_snapshot(self):
        text = json.dumps(B.snapshot())
        for secret in ('XdoLPWNt7ytn6BtU4FBf', 'DvW6ZBRAvK8C6HRZ68l3', 'G1QUjBCuRBbLbAmYlTgl', 'xi-api-key', 'ELEVENLABS_API_KEY'):
            self.assertNotIn(secret, text)

    def test_identity_is_kept_apart(self):
        sep = B.snapshot()['identity']['separation']
        self.assertTrue(all(c['ok'] for c in sep), sep)

    def test_cost_lock_is_closed(self):
        c = B.snapshot()['costs']
        self.assertEqual(c['lock']['state'], 'locked')
        self.assertFalse(c['lock']['gateway_enabled'])
        self.assertEqual(c['spend']['actual_units'], 0)

    def test_routes(self):
        self.assertEqual(self.req('GET', '/api/snapshot')[0], 200)
        code, body = self.req('GET', '/')
        self.assertEqual(code, 200); self.assertIn(b"const MODE = 'local'", body)
        self.assertEqual(self.req('GET', '/media/ep7/stills/b1.jpg')[0], 200)
        self.assertEqual(self.req('GET', '/media/../events.sqlite')[0], 404)
        self.assertEqual(self.req('POST', '/api/generate', {})[0], 405)
        self.assertEqual(self.req('PUT', '/api/decision', {})[0], 405)
        self.assertEqual(self.req('POST', '/api/decision', {'item': 'final-ep7', 'decision': 'publish_now'})[0], 400)

    def test_decisions_are_logged_and_approvals_lock(self):
        item = 'ep7-b1-b1_v3'
        self.assertEqual(self.req('POST', '/api/decision', {'item': item, 'decision': 'approved'})[0], 200)
        self.assertEqual(self.req('POST', '/api/decision', {'item': item, 'decision': 'rejected'})[0], 409)
        self.assertEqual(self.req('POST', '/api/decision', {'item': item, 'decision': 'changes_requested', 'note': 'v4'})[0], 200)
        rows = [r for r in B.log().rows(kind='review_decided') if r['data']['item'] == item]
        self.assertEqual([r['status'] for r in rows], ['approved', 'changes_requested'])
        self.assertEqual(rows[0]['scene'], 'b1')
        # the voice stage counts listening answers from the log
        s = B.snapshot(); q = next(i for i in s['inbox'] if i['type'] == 'voice' and i['project'] == 'timekeeper')
        serve.decide(B.log(), q['id'], 'article_missing')
        v = next(x for x in B.snapshot()['projects']['timekeeper']['videos'][0]['stages'] if x['stage'] == 'voice')
        self.assertEqual(v['units']['done'], 1)

    def test_page_decisions_ingest_with_the_same_rules(self):
        rows = {'a': {'item': 'ep7-b1-b1_v1', 'decision': 'approved', 'at': '2026-10-13T12:00:00Z'},
                'b': {'item': 'ep7-b1-b1_v1', 'decision': 'rejected', 'at': '2026-10-13T12:01:00Z'},
                'c': {'item': 'final-ep7', 'decision': 'publish_now', 'at': '2026-10-13T12:02:00Z'}}
        r = serve.ingest_rows(B.log(), rows)
        self.assertEqual((r['added'], len(r['refused'])), (1, 2))
        self.assertEqual(serve.ingest_rows(B.log(), rows)['skipped'], 1)          # running it again adds nothing

    def test_history_import_is_idempotent(self):
        n = len(B.log().rows())
        history.import_ep7(B.log(), S); history.import_royal_oak(B.log(), S)
        self.assertEqual(len(B.log().rows()), n)


class TestNoPaidPath(unittest.TestCase):
    def test_dashboard_code_never_touches_paid_components(self):
        import ast
        banned_mods = ('gateway', 'urllib', 'http.client', 'requests', 'socket')
        for f in (ROOT / 'director/dashboard').glob('*.py'):
            tree = ast.parse(f.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ''] + [a.name for a in node.names]
                else:
                    names = []
                for n in names:
                    self.assertFalse(any(b in n for b in banned_mods), f'{f.name} imports {n}')
                if isinstance(node, ast.Attribute):
                    self.assertNotIn(node.attr, ('synthesize', 'run_plan', 'approve'), f'{f.name} uses .{node.attr}')
        app = (ROOT / 'director/dashboard/app.html').read_text(encoding='utf-8')
        posts = set(re.findall(r"fetch\('([^']+)',\s*\{method:'POST'", app))
        self.assertEqual(posts, {'/api/decision'})


if __name__ == '__main__':
    unittest.main()
