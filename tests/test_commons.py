"""Real photographs first: only files whose own Commons page states a free licence, only when the file is what the scene
needs, credited on screen; the drawing stays the last resort. No network in tests (the search is replaced)."""
from tests import _guard  # noqa: F401
import subprocess, unittest

from tests.test_copilot import Env
from director.studio.store import Refused
from director.copilot import commons, orchestrator as O, styles


def png():
    return subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=gray:s=900x700', '-frames:v', '1', '-f', 'image2pipe',
                           '-vcodec', 'png', '-'], capture_output=True, check=True).stdout


def cand(title, lic='CC BY-SA 4.0', about=''):
    return {'title': title, 'page': 'https://commons.wikimedia.org/wiki/' + title.replace(' ', '_'), 'url': 'https://upload.wikimedia.org/x.jpg',
            'width': 900, 'height': 700, 'licence': lic, 'licence_url': 'https://creativecommons.org/licenses/by-sa/4.0', 'author': 'Clyde94',
            'name': '', 'about': about}


class TestRules(unittest.TestCase):
    def test_only_free_licences(self):
        for ok in ('CC BY-SA 4.0', 'CC BY 2.0', 'Public domain', 'CC0'): self.assertTrue(commons.licence_ok(ok), ok)
        for no in ('CC BY-NC 2.0', 'CC BY-ND 4.0', 'CC BY-NC-SA 3.0', 'Fair use', 'GFDL', '', 'All rights reserved'):
            self.assertFalse(commons.licence_ok(no), no)

    def test_only_the_picture_that_is_needed_and_never_a_replica(self):
        q = commons.query_for({'what': 'documented photograph of Hans Wilsdorf'})
        self.assertEqual(q, 'hans wilsdorf')
        self.assertEqual(commons.best(q, [cand('File:Rolex logo.svg.png'), cand('File:Hans Wilsdorf, fondatore di Rolex.jpg')])['title'],
                         'File:Hans Wilsdorf, fondatore di Rolex.jpg')
        # a description that happens to mention every word is not enough; a replica never counts
        self.assertIsNone(commons.best('oyster screw down crown', [cand('File:Rolex Daytona 126500LN.jpg', about='Oyster case, screw-down crown')]))
        self.assertIsNone(commons.best('rolex oyster 1926', [cand('File:Rolex Oyster 1926 replica.jpg')]))


class TestFound(Env):
    def setUp(self):
        super().setUp()
        self.orig = commons.candidates, commons.fetch, commons.enabled
        commons.candidates = lambda q, limit=10: [cand('File:Hans Wilsdorf, fondatore di Rolex e Tudor.jpg')] if 'wilsdorf' in q else []
        commons.fetch = lambda url: png()
        commons.enabled = lambda: True

    def tearDown(self):
        commons.candidates, commons.fetch, commons.enabled = self.orig
        super().tearDown()

    def test_a_found_photograph_is_licensed_by_its_page_credited_and_used_before_a_drawing(self):
        needs = [{'id': 'wilsdorf_portrait', 'scene': 'l6', 'what': 'documented photograph of Hans Wilsdorf', 'use': 'evidence'},
                 {'id': 'daily_mail_1927', 'scene': 'l12', 'what': 'scan of the 24 Nov 1927 Daily Mail front page', 'use': 'evidence'}]
        O._commons(self.S, self.pid, needs)
        assets = list(self.S.state(self.pid)['copilot']['assets'].values())
        self.assertEqual(len(assets), 1)                                  # nothing found for the newspaper: it keeps its drawing
        a = assets[0]
        self.assertEqual((a['status'], a['source'], a['slot'], a['scene']), ('verified', 'wikimedia-commons', 'wilsdorf_portrait', 'l6'))
        self.assertTrue(a['licence']['evidence'].startswith('https://commons.wikimedia.org/wiki/File:Hans_Wilsdorf'))
        self.assertIn('CC BY-SA 4.0', a['credit'])
        c = styles.choose({'prefer': ['technical_illustration'], 'theme': 'tk-bone'}, {'_id': 'l6', 'beat': 'claim', 'concepts': {}},
                          {a['slot']: a})
        self.assertEqual(c['technique'], 'archival_collage')
        self.assertIn('CC BY-SA 4.0', c['params']['tags'][0]['text'])     # the author and licence are on screen
        O._commons(self.S, self.pid, needs)                               # searched again: the same picture is not added twice
        self.assertEqual(len(self.S.state(self.pid)['copilot']['assets']), 1)

    def test_the_page_cannot_claim_a_found_picture(self):
        with self.assertRaises(Refused):
            self.owner('cp_asset', {'op': 'found', 'file': 'blobs/x.png', 'page': 'https://commons.wikimedia.org/wiki/File:x', 'licence': 'CC0'})
        with self.assertRaises(Refused):                                  # and not without a free licence on a Commons page
            self.S.act(self.pid, 'cp_asset', {'op': 'found', 'file': 'blobs/x.png', 'page': 'https://example.com/x', 'licence': 'CC0'}, actor='copilot')
        with self.assertRaises(Refused):
            self.S.act(self.pid, 'cp_asset', {'op': 'found', 'file': 'blobs/x.png', 'page': 'https://commons.wikimedia.org/wiki/File:x',
                                              'licence': 'CC BY-NC 2.0'}, actor='copilot')
