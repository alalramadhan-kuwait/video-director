"""The motion catalogue and the code agree; only implemented templates reach a film; every example builds."""
from tests import _guard  # noqa: F401
import json, re, shutil, subprocess, tempfile, unittest
from pathlib import Path

import yaml

from director.copilot import ai, styles
from director.studio import art, engine


class TestCatalogue(unittest.TestCase):
    def setUp(self):
        self.cat = {t['id']: t for t in art.catalogue()}

    def test_every_builder_and_registry_technique_is_catalogued_with_a_status(self):
        reg = yaml.safe_load(art.REGISTRY.read_text(encoding='utf-8'))['techniques']
        self.assertLessEqual(set(art.BUILDERS) | {t['id'] for t in reg}, set(self.cat))
        for t in self.cat.values():
            self.assertIn(t['status'], ('implemented', 'experimental', 'unavailable'), t['id'])
            if t['status'] == 'unavailable':
                self.assertNotIn(t['id'], art.BUILDERS); self.assertTrue(t.get('reason'), t['id'])
            elif t['status'] == 'experimental':
                self.assertTrue(t.get('reason'), t['id'])
            else:
                self.assertTrue(t['id'] in art.BUILDERS or t.get('engine'), t['id'])     # end card and transitions are engine features

    def test_the_plan_purposes_are_covered_by_implemented_templates(self):
        have = {p for t in self.cat.values() if t['status'] == 'implemented' for p in t['purpose']}
        for p in ('product', 'archive', 'timeline', 'mechanism', 'comparison', 'specification', 'place', 'quote', 'title',
                  'transition', 'end_card'):
            self.assertIn(p, have)

    def test_every_example_builds_a_scene(self):
        for t in self.cat.values():
            if t['id'] in art.BUILDERS:
                sc = art.scene_visual(t['id'], t['example'], t.get('theme', 'tk-bone'), 4.5, banner=t.get('name_ar'))
                self.assertTrue(sc['elements'], t['id'])

    def test_only_implemented_templates_are_production_ready(self):
        self.assertTrue(art.production_ready('spec_card'))
        self.assertFalse(art.production_ready('swiss_grid'))           # experimental: draws, never picked on its own
        self.assertFalse(art.production_ready('verified_3d'))          # unavailable
        st = {'id': 't', 'theme': 'tk-bone', 'prefer': ['swiss_grid', 'kinetic_type']}
        bs = {'concepts': {'swiss_grid': self.cat['swiss_grid']['example'], 'kinetic_type': self.cat['kinetic_type']['example']}}
        self.assertEqual(styles.choose(st, bs, {})['technique'], 'kinetic_type')
        lvl = {r['id']: r['level'] for r in art.support_matrix({})}
        self.assertEqual(lvl['swiss_grid'], 'prototype')

    def test_a_photo_template_waits_for_its_licensed_photo(self):
        st = {'id': 't', 'theme': 'tk-bone', 'prefer': ['product_reveal', 'kinetic_type']}
        bs = {'concepts': {'product_reveal': self.cat['product_reveal']['example'], 'kinetic_type': self.cat['kinetic_type']['example']}}
        self.assertEqual(styles.choose(st, bs, {})['technique'], 'kinetic_type')             # no verified photo: not the reveal
        self.assertEqual(styles.choose(st, bs, {'sample_watch': {'slot': 'sample_watch', 'use': 'illustration'}})['technique'], 'product_reveal')
        photo = {'slot': 'sub', 'scene': 'l4', 'use': 'evidence', 'what': 'Rolex Submariner 1953', 'credit': 'A · CC BY-SA 4.0'}
        got = styles.choose(st, {'_id': 'l4', 'beat': 'product', 'concepts': {}}, {'sub': photo})
        self.assertEqual((got['technique'], got['params']['asset'], got['params']['credit']), ('product_reveal', 'sub', 'A · CC BY-SA 4.0'))
        self.assertEqual(styles.choose(st, {'_id': 'l4', 'beat': 'person_real', 'concepts': {}}, {'sub': photo})['technique'], 'archival_collage')

    def test_the_ai_art_brief_knows_the_ready_templates_only(self):
        p = ai.system_prompt('art_brief')
        for tid in ('spec_card', 'quote_card', 'product_reveal', 'animated_timeline'):
            self.assertIn(f'- {tid} (', p)
        self.assertNotIn('- swiss_grid (', p)
        self.assertEqual(ai.system_prompt('script'), ai.SYSTEM['script'])


HAVE_RENDER = bool(shutil.which('ffmpeg') and shutil.which('node')) and engine.RENDER.is_file()


@unittest.skipUnless(HAVE_RENDER, 'node/ffmpeg not available')
class TestMusicDucksUnderTheVoice(unittest.TestCase):
    def _level(self, mp4, a, b):
        # music only: the 300 Hz test "voice" is notched out
        r = subprocess.run(['ffmpeg', '-v', 'info', '-ss', str(a), '-to', str(b), '-i', str(mp4), '-vn', '-af',
                            ','.join(['bandreject=f=300:width_type=h:w=60'] * 3) + ',volumedetect', '-f', 'null', '-'],
                           capture_output=True, text=True)
        return float(re.search(r'mean_volume: (-?[\d.]+)', r.stderr).group(1))

    def test_music_is_lower_while_the_voice_speaks_and_runs_to_the_end(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'sine=frequency=300:duration=3', str(d / 'v.wav')], check=True)
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'anoisesrc=d=12:c=pink:a=0.3', '-ar', '44100', str(d / 'm.wav')], check=True)
            sc = art.scene_visual('kinetic_type', {'lines': [{'text': 'اختبار', 'size': 60}]}, 'tk-bone', 9.0)
            sc.update(dur=9.0, voice='v.wav', voiceAt=3.0, silent=True)
            (d / 'sb.json').write_text(json.dumps({'width': 180, 'height': 320, 'fps': 5, 'dir': 'rtl', 'scenes': [sc]}, ensure_ascii=False))
            for name, extra in (('duck', ()), ('flat', ('--no-duck',))):
                engine.video(d / 'sb.json', d / f'{name}.mp4', scale=1, extra=('--music', str(d / 'm.wav'), '--music-gain', -18) + extra)
            out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a', '-show_entries', 'stream=duration', '-of', 'csv=p=0',
                                  str(d / 'duck.mp4')], capture_output=True, text=True).stdout
            self.assertGreater(float(out.strip()), 8.5)                                   # the music does not stop with the voice
            self.assertLess(self._level(d / 'duck.mp4', 3.5, 5.5), self._level(d / 'flat.mp4', 3.5, 5.5) - 5)   # ducked under the voice
            self.assertAlmostEqual(self._level(d / 'duck.mp4', 0.5, 2.5), self._level(d / 'flat.mp4', 0.5, 2.5), delta=1.0)   # full in pauses
