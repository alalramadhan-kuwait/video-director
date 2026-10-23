"""A film file becomes a film: catalogue-only templates, the brand's pronunciation, captions timed to the take,
omissions reported, sources and credits written. Offline: the mock voice (tones) and no music."""
from tests import _guard  # noqa: F401
import json, os, shutil, tempfile, unittest
from pathlib import Path

import yaml

from director import quickfilm
from director.studio import engine

HAVE_RENDER = bool(shutil.which('ffmpeg') and shutil.which('node')) and engine.RENDER.is_file()
FILM = {'title': 't', 'brand': 'timekeeper', 'seed': 't',
        'sources': ['[1] a source: https://example.org'],
        'lines': [{'id': 'l1', 'text': 'ساعة Panerai من 1936', 'say': 'ساعة Panerai من ألفٍ وتسعمئةٍ وستةٍ وثلاثين',
                   'template': 'kinetic_type', 'params': {'lines': [{'text': 'بانيراي', 'size': 90}]}},
                  {'id': 'l2', 'text': 'العلبة من رولكس', 'template': 'spec_card', 'banner': 'من صنع ماذا؟',
                   'params': {'title': 'الصانع', 'rows': [{'label': 'العلبة', 'value': 'رولكس'}]}}]}


class TestQuickFilm(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.env = {k: os.environ.get(k) for k in ('VD_DRAFT_VOICE', 'VD_MUSIC_CACHE')}     # other test modules set these too
        os.environ.update(VD_DRAFT_VOICE='offline-mock', VD_MUSIC_CACHE=str(self.d / 'music'))

    def tearDown(self):
        for k, v in self.env.items():
            if v is None: os.environ.pop(k, None)
            else: os.environ[k] = v
        shutil.rmtree(self.d, ignore_errors=True)

    def _file(self, film):
        f = self.d / 'film.yaml'; f.write_text(yaml.safe_dump(film, allow_unicode=True), encoding='utf-8'); return f

    def test_only_production_ready_templates(self):
        bad = json.loads(json.dumps(FILM)); bad['lines'][0]['template'] = 'swiss_grid'
        with self.assertRaises(ValueError):
            quickfilm.load(self._file(bad))
        self.assertEqual(len(quickfilm.load(self._file(FILM))['lines']), 2)

    def test_the_voice_says_the_brand_pronunciation_and_captions_keep_the_script(self):
        t = quickfilm.take(FILM['lines'][0], 'timekeeper', self.d / 'voice')
        self.assertIn('بانيراي', t['spoken']); self.assertNotIn('Panerai', t['spoken'])
        self.assertIn('ألفٍ', t['spoken'])                                   # `say` is what the voice reads
        self.assertEqual([w['w'] for w in t['words']], ['ساعة', 'Panerai', 'من', '1936'])   # captions keep the script
        self.assertTrue(all(w['s'] is not None and w['e'] > w['s'] for w in t['words']))
        again = quickfilm.take(FILM['lines'][0], 'timekeeper', self.d / 'voice')
        self.assertEqual(again['wav'], t['wav'])                             # cached by what is spoken

    def test_the_voice_script_is_what_the_voice_reads(self):
        recs = quickfilm.voice_script(FILM)
        self.assertEqual([r['id'] for r in recs], ['l1', 'l2'])
        self.assertIn('ألفٍ', recs[0]['text']); self.assertEqual(recs[1]['text'], 'العلبة من رولكس')

    @unittest.skipUnless(shutil.which('ffmpeg'), 'ffmpeg not available')
    def test_a_take_read_elsewhere_is_used_as_it_is_and_listened_to(self):
        import numpy as np
        from director.studio import voice
        given = self.d / 'omni'; given.mkdir()
        tone = lambda sec: voice.encode(0.3 * np.sin(np.linspace(0, 440 * 2 * np.pi * sec, int(voice.SR * sec))), 'wav')
        (given / 'l1.wav').write_bytes(tone(2.0))
        (given / 'l1.json').write_text(json.dumps({'provider': 'omnivoice', 'license_note': 'Upstream pretrained model: CC-BY-NC'}))
        t = quickfilm.take(FILM['lines'][0], 'timekeeper', self.d / 'voice', given=given)
        self.assertAlmostEqual(t['seconds'], 2.0, delta=0.2)                 # no speed change on a real take
        self.assertEqual([w['w'] for w in t['words']], ['ساعة', 'Panerai', 'من', '1936'])
        (given / 'l1.wav').write_bytes(tone(3.0))                            # the line read again is a new take
        self.assertNotEqual(quickfilm.take(FILM['lines'][0], 'timekeeper', self.d / 'voice', given=given)['wav'], t['wav'])
        label, lic = quickfilm.voice_label(given)
        self.assertIn('REVIEW', label); self.assertIn('not for publishing', label); self.assertIn('CC-BY-NC', lic)
        vox = self.d / 'vox'; vox.mkdir()
        (vox / 'l1.json').write_text(json.dumps({'provider': 'voxcpm2', 'license_note': 'Apache-2.0 weights: commercial use permitted'}))
        self.assertIn('commercial use permitted', quickfilm.voice_label(vox)[0])
        (vox / 'l2.json').write_text(json.dumps({'provider': 'omnivoice', 'license_note': 'CC-BY-NC'}))      # one review-only take
        self.assertIn('not for publishing', quickfilm.voice_label(vox)[0])
        with self.assertRaises(FileNotFoundError) as e:                      # every line needs its take
            quickfilm.make(self._file(FILM), self.d / 'out', video=False, voice_dir=given)
        self.assertIn('l2', str(e.exception))

    @unittest.skipUnless(HAVE_RENDER, 'node/ffmpeg not available')
    def test_a_film_file_makes_scenes_stills_and_credits(self):
        r = quickfilm.make(self._file(FILM), self.d / 'out', video=False)
        sb = json.loads((self.d / 'out/film.json').read_text())
        self.assertEqual([s.get('id') for s in sb['scenes'][:2]], ['l1', 'l2'])
        self.assertTrue(sb['scenes'][-1].get('endcard'))                     # the Time Keeper end card
        self.assertTrue(all(s['words'] and s['voice'].startswith('voice/') for s in sb['scenes'][:2]))
        self.assertEqual(r['layout'], [])
        self.assertEqual(len(r['stills']), 2)
        self.assertIsNone(r['music'])                                        # offline: no music, never a broken one
        self.assertIn('[1] a source', (self.d / 'out/credits.txt').read_text())
        self.assertIn('DRAFT', r['label'])
