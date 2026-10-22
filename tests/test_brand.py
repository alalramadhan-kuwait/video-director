"""One brand config drives fonts, captions, narration, pronunciation and music; music only with a licence record."""
from tests import _guard  # noqa: F401
import json, tempfile, unittest
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

    def test_music_only_with_a_commercial_licence_record(self):
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
                self.assertEqual(B.music(), (lib / 'bed.mp3', -24.0))
            finally:
                B.load = orig
