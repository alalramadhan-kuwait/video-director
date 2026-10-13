"""Dashboard: real progress only, append-only history, locked approvals, and no path to a paid provider."""
from tests import _guard  # noqa: F401
import io, json, re, shutil, sqlite3, tempfile, unittest
from pathlib import Path
from unittest import mock

from director import events as E
from director.events import EventLog
from director.dashboard import build as B, history, serve, sync
from director.dashboard.snapshot import classify
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

    def req(self, method, path, body=None, headers=None, full=False):
        h = object.__new__(serve.Handler)
        raw = json.dumps(body).encode() if body is not None else b''
        h.rfile, h.wfile = io.BytesIO(raw), io.BytesIO()
        h.headers = {'Content-Length': str(len(raw)), **(headers or {})}
        h.path, h.command, h.request_version, h.requestline = path, method, 'HTTP/1.1', f'{method} {path} HTTP/1.1'
        h.client_address, h.close_connection = ('127.0.0.1', 0), True
        getattr(h, 'do_' + method)()
        out = h.wfile.getvalue()
        code = int(out.split(b' ', 2)[1])
        head, body = out.split(b'\r\n\r\n', 1)
        return (code, head.decode('latin-1'), body) if full else (code, body)

    def proof(self, check, **over):
        """What the browser reports after really playing the flagged word of a listening check."""
        p = {'src': 'media/' + check['audio'].split('media/', 1)[1], 'duration': check['duration'],
             'played': [[max(0, check['word_s'] - 0.3), check['word_e'] + 0.1]], 'error': None}
        return {**p, **over}

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
        self.assertTrue(body.startswith(b'<!doctype html>'))
        self.assertIn(b'name="viewport" content="width=device-width', body)          # a phone gets the phone layout
        self.assertEqual(self.req('GET', '/media/ep7/stills/b1.jpg')[0], 200)
        self.assertEqual(self.req('GET', '/media/../events.sqlite')[0], 404)
        self.assertEqual(self.req('POST', '/api/generate', {})[0], 405)
        self.assertEqual(self.req('PUT', '/api/decision', {})[0], 405)
        self.assertEqual(self.req('POST', '/api/decision', {'item': 'final-ep7', 'decision': 'publish_now'})[0], 422)
        self.assertEqual(self.req('POST', '/api/decision', {'item': 'ep9-zz-v1', 'decision': 'approved'})[0], 400)

    def test_media_byte_ranges(self):
        """iPhone Safari will not play audio or video unless the server answers byte ranges."""
        f = B.MEDIA / 'royal-oak/audio/p2-q.mp3'; n = f.stat().st_size
        code, head, body = self.req('GET', '/media/royal-oak/audio/p2-q.mp3', headers={'Range': 'bytes=0-1'}, full=True)
        self.assertEqual((code, len(body)), (206, 2)); self.assertIn(f'Content-Range: bytes 0-1/{n}', head)
        self.assertEqual(body, f.read_bytes()[:2])
        code, head, body = self.req('GET', '/media/royal-oak/audio/p2-q.mp3', headers={'Range': 'bytes=-10'}, full=True)
        self.assertEqual((code, body), (206, f.read_bytes()[-10:]))
        self.assertEqual(self.req('GET', '/media/royal-oak/audio/p2-q.mp3', headers={'Range': f'bytes={n}-'})[0], 416)
        code, head, body = self.req('GET', '/media/royal-oak/audio/p2-q.mp3', full=True)
        self.assertEqual(code, 200); self.assertIn('Accept-Ranges: bytes', head)
        code, head, body = self.req('HEAD', '/media/royal-oak/audio/p2-q.mp3', full=True)
        self.assertEqual((code, body), (200, b'')); self.assertIn(f'Content-Length: {n}', head)

    def test_decisions_are_logged_and_approvals_lock(self):
        item = 'ep7-b1-b1_v3'
        self.assertEqual(self.req('POST', '/api/decision', {'item': item, 'decision': 'approved'})[0], 200)
        self.assertEqual(self.req('POST', '/api/decision', {'item': item, 'decision': 'rejected'})[0], 409)
        self.assertEqual(self.req('POST', '/api/decision', {'item': item, 'decision': 'changes_requested', 'note': 'v4'})[0], 200)
        rows = [r for r in B.log().rows(kind='review_decided') if r['data']['item'] == item]
        self.assertEqual([r['status'] for r in rows], ['approved', 'changes_requested'])
        self.assertEqual(rows[0]['scene'], 'b1')
        # the voice stage counts listening answers from the log, and only answers given with playback proof get there
        q = B.snapshot()['inbox_checks'][0]
        self.assertEqual(serve.decide(B.log(), q['id'], 'article_missing', playback=self.proof(q))['status'], 'recorded')
        v = next(x for x in B.snapshot()['projects']['timekeeper']['videos'][0]['stages'] if x['stage'] == 'voice')
        self.assertEqual(v['units']['done'], 1)

    def test_listening_answer_needs_proof_the_word_played(self):
        checks = B.snapshot()['inbox_checks']
        self.assertEqual(len(checks), 10); self.assertEqual(len({c['line'] for c in checks}), 8)
        q, other = checks[0], next(c for c in checks if c['audio_file'] != checks[0]['audio_file'])
        bad = {'no record': None,
               'another file': self.proof(q, src='media/' + other['audio'].split('media/', 1)[1]),
               'did not load (0:00 / 0:00)': self.proof(q, duration=0),
               'word not played': self.proof(q, played=[[0, max(0.1, q['word_s'] - 2)]]),
               'audio error': self.proof(q, error=4)}
        for why, pb in bad.items():
            code, body = self.req('POST', '/api/decision', {'item': q['id'], 'decision': 'article_heard', 'playback': pb})
            self.assertEqual(code, 422, why); self.assertEqual(json.loads(body)['status'], 'refused', why)
        self.assertFalse([r for r in B.log().rows(kind='review_decided') if r['data']['item'] == q['id']])
        # a playback failure can be reported, but it is not a listening result
        self.assertEqual(serve.decide(B.log(), q['id'], 'playback_failed')['status'], 'recorded')
        v = next(x for x in B.snapshot()['projects']['timekeeper']['videos'][0]['stages'] if x['stage'] == 'voice')
        self.assertEqual(v['units']['done'], 0)
        code, body = self.req('POST', '/api/decision', {'item': q['id'], 'decision': 'unsure', 'playback': self.proof(q)})
        self.assertEqual(code, 200)
        rec = [r for r in B.log().rows(kind='review_decided') if r['data']['item'] == q['id']][-1]
        self.assertEqual(rec['data']['playback']['played'], self.proof(q)['played'])            # the proof is kept

    def test_sync_outcomes_and_idempotency(self):
        q = B.snapshot()['inbox_checks'][0]
        serve.decide(B.log(), 'ep7-b2-final', 'approved', at='2026-10-13T12:00:00.000Z')
        serve.decide(B.log(), 'f_70dc55998b', 'dismissed', at='2026-10-13T12:00:05.000Z')
        docs = [{'_doc': 'a', 'decision_id': 'a', 'item': 'concept-ep7-b3-scientific_diagram', 'decision': 'concept_selected', 'at': '2026-10-13T12:01:00.000Z'},
                {'_doc': 'b', 'decision_id': 'b', 'item': 'concept-ep7-b3-scientific_diagram', 'decision': 'concept_selected', 'at': '2026-10-13T12:02:00.000Z'},
                {'_doc': 'c', 'decision_id': 'c', 'item': 'ep7-b2-final', 'decision': 'rejected', 'at': '2026-10-13T12:01:00.000Z'},
                {'_doc': 'd', 'decision_id': 'd', 'item': 'f_70dc55998b', 'decision': 'accepted', 'at': '2026-10-13T12:00:04.500Z'},
                {'_doc': 'e', 'decision_id': 'e', 'item': q['id'], 'decision': 'article_heard', 'at': '2026-10-13T12:01:00.000Z'},
                {'_doc': 'f', 'decision_id': 'f', 'item': q['id'], 'decision': 'unsure', 'playback': self.proof(q), 'at': '2026-10-13T12:01:30.000Z'},
                {'_doc': 'g', 'decision_id': 'g', 'item': 'ep9-zz-v1', 'decision': 'approved', 'at': '2026-10-13T12:01:00.000Z'},
                {'_doc': 'h', '_error': 'unreadable export file'}]
        n0 = len(B.log().rows(kind='review_decided'))
        r = sync.ingest(B.log(), docs, 'artifact')
        st = {x['decision_id']: x['status'] for x in r['receipts']}
        self.assertEqual(st, {'a': 'recorded', 'b': 'duplicate', 'c': 'conflict', 'd': 'conflict', 'e': 'refused',
                              'f': 'recorded', 'g': 'failed', 'h': 'failed'})
        self.assertEqual(len(B.log().rows(kind='review_decided')) - n0, 2)
        self.assertEqual(len(B.log().rows(kind='sync')), 6)                    # every outcome that was not recorded
        receipts = sync.receipts_for_page(r)
        self.assertEqual({w['doc_id'] for w in receipts}, set('abcdefgh'))
        self.assertTrue(all(w['collection'] == 'sync' and w['op'] == 'set' for w in receipts))
        again = sync.ingest(B.log(), docs, 'artifact')                       # same export again: nothing changes
        self.assertEqual(again['summary']['recorded'], 0)
        self.assertEqual({x['decision_id']: x['event'] for x in again['receipts'] if x['decision_id'] in 'af'},
                         {x['decision_id']: x['event'] for x in r['receipts'] if x['decision_id'] in 'af'})
        self.assertEqual(len(B.log().rows(kind='review_decided')) - n0, 2)
        self.assertEqual(len(B.log().rows(kind='sync')), 6)

    def test_sync_compares_times_as_instants(self):
        """Event-log times have no milliseconds; '12:00:05Z' must not count as later than '12:00:05.400Z'."""
        serve.decide(B.log(), 'f_70dc55998b', 'dismissed', at='2026-10-13T12:00:05Z')
        r = sync.ingest(B.log(), [{'_doc': 'x', 'decision_id': 'x', 'item': 'f_70dc55998b', 'decision': 'accepted',
                                   'at': '2026-10-13T12:00:05.400Z'}], 'artifact')
        self.assertEqual(r['receipts'][0]['status'], 'recorded')
        r = sync.ingest(B.log(), [{'_doc': 'y', 'decision_id': 'y', 'item': 'f_70dc55998b', 'decision': 'needs_source',
                                   'at': 'yesterday'}], 'artifact')
        self.assertEqual(r['receipts'][0]['status'], 'failed')

    def test_load_export_formats(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t) / 'decisions'; d.mkdir()
            (d / 'a.json').write_text(json.dumps({'id': 'a', 'data': {'decision_id': 'a', 'item': 'final-ep7', 'decision': 'approved'}}))
            (d / 'b.json').write_text('{"broken": ')
            got = sync.load_export(t)
            self.assertEqual([(x['_doc'], x.get('item'), bool(x.get('_error'))) for x in got], [('a', 'final-ep7', False), ('b', None, True)])
            f = Path(t) / 'list.json'
            f.write_text(json.dumps({'docs': [{'id': 'z', 'data': {'decision_id': 'z', 'item': 'final-ep7', 'decision': 'rejected'}}]}))
            self.assertEqual(sync.load_export(f)[0]['decision'], 'rejected')

    def test_one_art_task_per_scene_and_every_finding_kept(self):
        s = B.snapshot()
        rep = json.loads((ROOT / 'var/review/ep7-final/artistic_report.json').read_text(encoding='utf-8'))
        source = {f['id'] for f in rep['ai_judgement'] + rep['automated']}
        scenes = [x['id'] for x in s['projects']['diabetes-history']['videos'][0]['scenes']]
        art = [t for t in s['review_tasks'] if t['type'] == 'art' and t['video'] == 'ep7']
        self.assertEqual(sorted(t['scene'] for t in art), sorted(scenes))
        ids = [f['id'] for t in art for f in t['findings']]
        self.assertEqual(len(ids), len(set(ids)))                              # never counted twice
        self.assertEqual(set(ids), source)                                     # none lost
        for t in art:
            self.assertEqual(sum(t['buckets'].values()), len(t['findings']))
            self.assertTrue(all(f['source'] and f['reviewer'] is not None for f in t['findings']))
        final = next(t for t in s['review_tasks'] if t['id'] == 'final-ep7')
        self.assertNotIn('findings', final)                                    # the final video does not repeat them

    def test_buckets(self):
        f = lambda **k: {'dimension_label': 'Composition and visual hierarchy', 'severity': 'minor', 'confidence': 'high', 'notes': [], **k}
        self.assertEqual(classify(f(notes=['claim shown without a cited fact'])), 'blocked')
        self.assertEqual(classify(f(dimension_label='Readability of Arabic text', severity='critical')), 'fixable')
        self.assertEqual(classify(f()), 'fixable')
        self.assertEqual(classify(f(dimension_label='Lighting, colours and character proportions')), 'suggestion')
        self.assertEqual(classify(f(dimension_label='Lighting, colours and character proportions', severity='major')), 'fixable')
        self.assertEqual(classify(f(dimension_label='Motion and pacing', severity='major')), 'decide')
        self.assertEqual(classify(f(dimension_label='Motion and pacing')), 'suggestion')
        self.assertEqual(classify(f(dimension_label='Historical and technical accuracy')), 'decide')
        self.assertEqual(classify(f(dimension_label='Historical and technical accuracy', confidence='low')), 'suggestion')

    def test_concepts_are_proposals_and_free(self):
        for sc in B.snapshot()['projects']['diabetes-history']['videos'][0]['scenes']:
            for o in (sc.get('concepts') or {}).get('options', []):
                self.assertEqual(o['kind'], 'proposal')
                self.assertTrue(o['cost'].startswith('free'), o['cost'])          # nothing here would spend money
                if o['preview']:
                    self.assertEqual(o['preview']['kind'], 'reference')
                    self.assertIn('Not drawn for ' + sc['id'], o['preview']['label'])
                if o['decision']:
                    self.assertNotEqual(o['decision']['decision'], 'approved')      # selecting is not approving

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
