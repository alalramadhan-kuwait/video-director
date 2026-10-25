"""Delivery by platform, words kept clear of the app's buttons, cuts on the music's beats, the written hook
(practices taken from video-ad-editor)."""
from tests import _guard  # noqa: F401
import shutil, tempfile, unittest
from pathlib import Path

import numpy as np

from director import beats, platforms, quickfilm
from director.studio import art, engine


class TestPlatforms(unittest.TestCase):
    def test_names_and_the_brand_default(self):
        self.assertEqual(platforms.get('instagram-reels')[0], 'reels')
        self.assertEqual(platforms.get('TikTok')[0], 'tiktok')
        self.assertEqual(platforms.get(None)[0], 'reels')
        self.assertEqual(platforms.of({'platform': 'whatsapp'}, {'export': {'platform': 'tiktok'}})[0], 'whatsapp')
        self.assertEqual(platforms.of({}, {'export': {'platform': 'tiktok'}})[0], 'tiktok')
        with self.assertRaises(ValueError):
            platforms.get('myspace')

    def test_zones_in_storyboard_pixels_and_tiktok_captions_higher(self):
        z = {d['k']: d for d in platforms.zones(platforms.get('reels')[1])}
        self.assertEqual(z['top (account name, follow)']['h'], 100)
        self.assertEqual(z['right (like, comment, share)']['x'], round(950 * 720 / 1080, 1))
        self.assertLess(platforms.get('tiktok')[1]['caption_y'], platforms.get('reels')[1]['caption_y'])
        self.assertEqual(platforms.zones(platforms.get('whatsapp')[1]), [])

    def test_length_and_parts_cut_between_scenes(self):
        self.assertIsNone(platforms.length_warning(platforms.get('reels')[1], 170))
        self.assertIn('180', platforms.length_warning(platforms.get('reels')[1], 202))
        durs = [30, 30, 30, 30, 30, 20]
        starts = [sum(durs[:i]) for i in range(len(durs))]
        got = platforms.parts(starts, durs, 85)
        self.assertEqual(got, [(0, 60), (60, 120), (120, 170)])
        self.assertTrue(all(b - a <= 85 for a, b in got))
        self.assertEqual(platforms.parts([0, 100], [100, 10], 85), [(0, 100), (100, 110)])     # one long scene stays whole


def clicks(first=0.23, every=0.5, n=24, sr=beats.SR):
    a = np.zeros(int(sr * (first + every * n + 1)), dtype=np.float32)
    for i in range(n):
        s = int((first + i * every) * sr)
        a[s:s + 300] += np.random.default_rng(i).standard_normal(300).astype(np.float32) * .8
    return a


class TestBeats(unittest.TestCase):
    def test_the_clicks_are_found_where_they_are(self):
        t, s = beats.onsets(clicks())
        self.assertEqual(len(t), 24)
        self.assertTrue(np.all(np.abs(t - (0.23 + 0.5 * np.arange(24))) < 0.04))
        self.assertTrue(np.all((0 < s) & (s <= 1)))

    def test_the_music_shifts_so_the_cuts_land_on_beats(self):
        t, s = beats.onsets(clicks())
        cuts = [1.0, 2.5, 4.0]
        o, hits = beats.best_offset(t, s, cuts, later=2.0, earlier=1.0)
        self.assertEqual(hits, 3)
        self.assertTrue(all(beats.on_beat(t, cuts, o)))
        self.assertEqual(beats.best_offset(t, s, cuts, 0, 0), (0.0, 0))                 # no room to move: the music stays

    def test_punch_pushes_only_a_camera_that_starts_at_zero(self):
        sc = {'camera': {'zoom': [[0, 1.0], [4.0, 1.06, 'inOutCubic']], 'x': [[0, 360]], 'y': [[0, 640]]}}
        self.assertTrue(beats.punch(sc))
        self.assertEqual(sc['camera']['zoom'][:2], [[0, 1.025], [0.35, 1.0, 'outCubic']])
        self.assertEqual(sc['camera']['zoom'][-1], [4.0, 1.06, 'inOutCubic'])
        self.assertFalse(beats.punch({'elements': []}))

    def test_align_writes_a_shifted_track_only_when_it_moves(self):
        import subprocess
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            raw = d / 'm.f32'; raw.write_bytes(clicks().tobytes())
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(beats.SR), '-ac', '1', '-i', str(raw), str(d / 'm.wav')], check=True)
            r = beats.align(d / 'm.wav', [1.0, 2.5, 4.0], 5.0, d / 'a.flac', max_later=2.0, max_delay=1.0)
            self.assertEqual(r['hits'], 3)
            self.assertEqual(r['file'], d / 'a.flac' if r['offset'] else d / 'm.wav')


class TestHook(unittest.TestCase):
    def test_the_hook_is_big_and_the_captions_wait_for_it(self):
        sc = {'theme': 'tk-black', 'elements': [], 'words': [[0.3, 'قصة'], [1.2, 'ساعة'], [2.6, 'في']]}
        dur = quickfilm.hook_card(sc, {'text': 'ساعة صُنعت لعتمة البحر|وعاشت سرًّا عسكريًا', 'em': ['سرًّا عسكريًا'], 'dur': 2.3})
        self.assertEqual(dur, 2.3)
        self.assertEqual(sc['words'], [[2.6, 'في']])
        el = sc['elements'][0]
        self.assertIn(art.GOLD, el['html']); self.assertIn('<br>', el['html']); self.assertIn(art.PAPER, el['html'])
        self.assertEqual(el['out']['at'], 2.0)
        self.assertEqual(quickfilm.hook_seconds({'text': 'كلمة'}), 1.6)
        self.assertEqual(quickfilm.hook_seconds({'text': ' '.join(['كلمة'] * 12)}), 3.0)

    def test_a_hook_the_story_does_not_say_is_reported(self):
        film = quickfilm.load(engine.ROOT / 'films/panerai.yaml')
        self.assertEqual([m for m in quickfilm.story_check(film) if m.startswith('hook')], [])
        film['hook'] = {'text': 'أغلى ساعة في العالم'}
        self.assertTrue(any(m.startswith('hook') for m in quickfilm.story_check(film)))


HAVE_RENDER = bool(shutil.which('ffmpeg') and shutil.which('node')) and engine.RENDER.is_file()


@unittest.skipUnless(HAVE_RENDER, 'node/ffmpeg not available')
class TestSafeZones(unittest.TestCase):
    def test_words_under_the_buttons_are_found_and_a_credit_is_clear_of_them(self):
        sc = art.scene_visual('kinetic_type', {'lines': [{'text': 'في الوسط', 'size': 60}]}, 'tk-bone', 3.0)
        sc['dur'] = 3.0
        sc['elements'] += [{'type': 'text', 'text': 'تحت الأزرار', 'font': 'cap', 'size': 26, 'color': '#111', 'x': 360, 'y': 40, 'depth': 0},
                           {'type': 'text', 'text': 'Credit · CC BY 4.0', 'font': 'cap', 'size': 18, 'color': '#111', 'x': 360,
                            'y': art.CREDIT_Y, 'depth': 0}]
        sb = {'width': 720, 'height': 1280, 'fps': 30, 'dir': 'rtl', **art.style('timekeeper'), 'scenes': [sc]}
        with tempfile.TemporaryDirectory() as d:
            out = engine.safe(sb, Path(d), platforms.zones(platforms.get('reels')[1]))
        hard = [l for l in out if l.startswith('safe HARD')]
        self.assertEqual(len(hard), 1, out)
        self.assertIn('تحت الأزرار', hard[0]); self.assertIn('top', hard[0])
        self.assertIn("1 word(s) under the app's buttons", out[-1])


if __name__ == '__main__':
    unittest.main()
