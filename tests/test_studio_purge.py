"""The studio's weekly purge (tools/studio/purge-plan.py, moved from staging on 9 Nov 2026 so the weekly task can run it):
it deletes only ids he ticked, still hidden 30+ days before the question, and only the exact files they name."""
from tests import _guard  # noqa: F401
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / 'tools/studio/purge-plan.py'
ASKED = '2026-11-07T10:00:00Z'


def run(*args):
    return subprocess.run([sys.executable, str(PLAN), *map(str, args)], capture_output=True, text=True)


class Purge(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp())
        (self.t / 'films').mkdir(); (self.t / 'inbox').mkdir()
        films = {
            'rubies': {'name': 'الياقوت', 'kind': 'reel', 'version': 'v11', 'hidden': True, 'hidden_at': '2026-09-01T00:00:00Z',
                       'video': 'film/rubies-v11.mp4', 'final': '/_blob/' + 'a' * 32},
            'rubies-engraving': {'name': 'الياقوت · نقش', 'kind': 'reel', 'version': 'v1', 'video': 'film/rubies-engraving-v1.mp4'},
            'recent': {'name': 'جديد', 'kind': 'reel', 'version': 'v1', 'hidden': True, 'hidden_at': '2026-11-01T00:00:00Z',
                       'video': '/_blob/' + 'b' * 32},
            'shared': {'name': 'مشترك', 'kind': 'reel', 'version': 'v1', 'hidden': True, 'hidden_at': '2026-09-01T00:00:00Z',
                       'video': '/_blob/' + 'c' * 32},
            'keeper': {'name': 'باقي', 'kind': 'reel', 'version': 'v1', 'video': '/_blob/' + 'c' * 32},
        }
        for k, v in films.items(): (self.t / 'films' / f'{k}.json').write_text(json.dumps(v, ensure_ascii=False))
        self.q = self.t / 'q.json'
        self.q.write_text(json.dumps({'asked_at': ASKED, 'status': 'open', 'films': [{'id': i} for i in ('rubies', 'recent', 'shared')]}))

    def answer(self, **row):
        (self.t / 'inbox' / 'r.json').write_text(json.dumps({'kind': 'answer', 'key': 'purge', 'asked_at': ASKED, 'at': '2026-11-07T12:00:00Z', **row}))

    def delete_list(self):
        r = run('delete', '--films', self.t / 'films', '--inbox', self.t / 'inbox', '--purge', self.q, '--out', self.t / 'out')
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads((self.t / 'out' / 'delete-list.json').read_text())

    def test_only_ticked_ids_hidden_long_enough_with_their_exact_files(self):
        self.answer(answer='yes', ids=['rubies', 'recent', 'shared'], asked=['rubies', 'recent', 'shared'])
        d = {x['id']: x for x in self.delete_list()['delete']}
        self.assertEqual(sorted(d), ['rubies', 'shared'])                 # «recent» was hidden less than 30 days before
        self.assertEqual(d['rubies']['files'], sorted(['film/rubies-v11.mp4', '/_blob/' + 'a' * 32]))
        self.assertNotIn('film/rubies-engraving-v1.mp4', d['rubies']['files'])   # never a prefix match
        self.assertEqual(d['shared']['files'], [])                         # a file another film still uses is kept
        self.assertEqual(d['shared']['files_kept'], ['/_blob/' + 'c' * 32])

    def test_no_answer_or_a_yes_without_ids_deletes_nothing(self):
        self.assertEqual(self.delete_list()['delete'], [])
        self.answer(answer='yes', via='chat')
        self.assertEqual(self.delete_list()['delete'], [])

    def test_recheck_refuses_a_film_he_restored(self):
        rec = self.t / 'rec.json'
        rec.write_text(json.dumps({'hidden': True, 'hidden_at': '2026-09-01T00:00:00Z'}))
        self.assertEqual(run('recheck', '--record', rec, '--purge', self.q).returncode, 0)
        rec.write_text(json.dumps({'hidden': False}))
        self.assertEqual(run('recheck', '--record', rec, '--purge', self.q).returncode, 1)

    def test_ask_lists_films_hidden_30_days(self):
        r = run('ask', '--films', self.t / 'films', '--inbox', self.t / 'inbox', '--now', '2026-11-14T10:00:00Z', '--out', self.t / 'ask')
        self.assertEqual(r.returncode, 0, r.stderr)
        ids = [x['id'] for x in json.loads((self.t / 'ask' / 'studio-purge.json').read_text())['films']]
        self.assertEqual(sorted(ids), ['rubies', 'shared'])


if __name__ == '__main__':
    unittest.main()
