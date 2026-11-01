"""A picture we made with AI keeps its credit in credits.txt, never on screen (the owner: «الناس تدري»)."""
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from director import quickfilm


class AICreditOffScreen(unittest.TestCase):
    def _film(self, d: Path) -> dict:
        Image.new('RGB', (60, 80), 'white').save(d / 'pose.png')
        Image.new('RGB', (80, 60), 'white').save(d / 'shop.jpg')
        return {'photos': {
            'pose': {'file': str(d / 'pose.png'), 'licence': 'AI illustration', 'credit': 'رسم بالذكاء الاصطناعي · من صورة ملفه الصحفي'},
            'shop': {'file': str(d / 'shop.jpg'), 'licence': 'credited', 'credit': 'Phillips', 'page': 'https://example.org/lot'},
        }}

    def test_ai_drawing_has_no_credit_on_screen(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            pics = quickfilm.photos(self._film(d), d / 'work')
            self.assertEqual(quickfilm.screen_credit(pics, 'pose'), '')
            self.assertIn('الذكاء', pics['pose']['credit'])            # still credited in credits.txt
            self.assertEqual(quickfilm.screen_credit(pics, 'shop'), 'Phillips')

    def test_cached_assets_still_hide_it(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            film = self._film(d)
            quickfilm.photos(film, d / 'work')
            pics = quickfilm.photos(film, d / 'work')                  # the second build reads the licence record
            self.assertEqual(quickfilm.screen_credit(pics, 'pose'), '')

    def test_ai_drawn(self):
        self.assertTrue(quickfilm.ai_drawn({'licence': 'AI illustration'}))
        self.assertFalse(quickfilm.ai_drawn({'licence': 'credited'}))
        self.assertFalse(quickfilm.ai_drawn({}))


if __name__ == '__main__':
    unittest.main()
