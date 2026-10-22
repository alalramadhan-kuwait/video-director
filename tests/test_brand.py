"""One brand config drives fonts, captions, narration, pronunciation and music; music only with a licence record."""
from tests import _guard  # noqa: F401
import json, os, tempfile, unittest
from pathlib import Path

from director import brand as B
from director.studio import art


class TestBrand(unittest.TestCase):
    def test_fonts_and_captions_reach_the_renderer(self):
        s = art.style('timekeeper')
        cfg = B.load('timekeeper')
        self.assertEqual(s['style']['banner']['font'], cfg['fonts']['banner'])
        self.assertEqual(s['style']['caption']['font'], cfg['fonts']['caption'])
        self.assertEqual((s['style']['caption']['bg'], s['style']['caption']['ink']), (cfg['captions']['bg'], cfg['captions']['ink']))
        self.assertEqual(s['captionSize'], cfg['captions']['size'])
        self.assertIn('tk-bone', s['themes'])
        self.assertEqual(art.style('diabetes-history')['style'].get('caption', {}).get('font'), json.loads(
            (B.ROOT / 'director/studio/assets/tk-style.json').read_text())['style']['caption']['font'])   # no config: unchanged

    def test_watch_names_are_said_right_and_captions_keep_the_script(self):
        t = 'ساعة Panerai Luminor مقابل Rolex Submariner و Grand Seiko و Seiko'
        self.assertEqual(B.spoken(t), 'ساعة بانيراي لومينور مقابل رولكس صبمارينر و غراند سيكو و سيكو')
        self.assertEqual(B.spoken('Seikos'), 'Seikos')                      # whole words only

    def test_own_track_only_with_a_commercial_licence_record(self):
        with tempfile.TemporaryDirectory() as d:
            lib = Path(d)
            orig = B.load
            B.load = lambda brand=None: {'music': {'library': str(lib), 'gain_db': -24}}
            try:
                (lib / 'bed.mp3').write_bytes(b'x')
                self.assertIsNone(B.music())                                   # no record: no music
                (lib / 'bed.licence.json').write_text(json.dumps({'licence': 'NC only', 'source': 'https://x', 'commercial_use': False}))
                self.assertIsNone(B.music())                                   # not for commercial use: no music
                (lib / 'bed.licence.json').write_text(json.dumps({'licence': 'Pixabay Content License', 'source': 'https://pixabay.com/music/x'}))
                m = B.music()
                self.assertEqual((m['file'], m['gain'], m['licence']), (lib / 'bed.mp3', -24.0, 'Pixabay Content License'))
            finally:
                B.load = orig

    def test_the_whole_catalogue_is_listed_with_its_licence(self):
        cat = json.loads((B.ROOT / 'brand/music/incompetech.json').read_text())
        self.assertGreater(len(cat['tracks']), 1000)
        self.assertEqual((cat['licence'], cat['commercial_use']), ('CC BY 4.0', True))
        t = B.choose(title='Gymnopedie No. 1')
        self.assertEqual(t['source'], 'https://incompetech.com/music/royalty-free/mp3-royaltyfree/Gymnopedie%20No%201.mp3')
        self.assertTrue(t['credit'].startswith('"Gymnopedie No. 1" Kevin MacLeod (incompetech.com)'))
        self.assertIn('Attribution 4.0', t['credit'])

    def test_the_film_gets_a_calm_track_that_fits_the_brand(self):
        m = B.load()['music']
        picks = {B.choose(seconds=150, seed=f'film-{i}')['title'] for i in range(40)}
        self.assertGreater(len(picks), 3)                                      # films differ
        self.assertEqual(B.choose(seconds=150, seed='panerai'), B.choose(seconds=150, seed='panerai'))   # same film, same track
        for t in B.ranked(seconds=150)[:30]:
            self.assertFalse(set(t['feel']) & set(m['avoid']), t['title'])
            self.assertLessEqual(t.get('bpm') or 0, m['max_bpm'])
            self.assertTrue(set(t['feel']) & set(m['prefer']))
            self.assertFalse(any(w in f"{t['title']} {t['instruments']} {t['about']}".lower() for w in m['avoid_words']), t['title'])
        self.assertTrue(all(t['seconds'] >= 150 for t in B.ranked(seconds=150)[:10]))   # long enough not to loop

    def test_offline_means_no_music_never_a_broken_one(self):
        with tempfile.TemporaryDirectory() as d:
            os.environ['VD_MUSIC_CACHE'] = d
            try:
                self.assertIsNone(B.music(seconds=60, seed='x'))               # tests block the network: no download, no music
                t = B.choose(seconds=60, seed='x')
                (Path(d) / t['file']).write_bytes(b'ID3' + b'\0' * 60000)    # already in the cache with its record: used
                (Path(d) / t['file']).with_suffix('.licence.json').write_text(json.dumps({'licence': t['licence'], 'source': t['source']}))
                m = B.music(seconds=60, seed='x')
                self.assertEqual((m['title'], m['licence']), (t['title'], 'CC BY 4.0'))
                self.assertIn('Kevin MacLeod', m['credit'])
            finally:
                os.environ.pop('VD_MUSIC_CACHE')
