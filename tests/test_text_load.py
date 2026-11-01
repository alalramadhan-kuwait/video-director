"""Captions + one block of words at a time (the owner: «more than 3 lines of words … caption, title, sub title. it is too much»)."""
from tests import _guard  # noqa: F401
import unittest

from director.studio import engine, textload


def scene(banner='عنوان', *els):
    return {'id': 'l1', 'banner': banner, 'elements': list(els)}


class TextLoad(unittest.TestCase):
    def test_a_banner_alone_stays(self):
        sc = scene('عنوان', {'type': 'text', 'text': 'Phillips', 'size': 18, 'in': {'at': .5}})   # a credit is not a block
        self.assertIsNone(textload.budget(sc))
        self.assertEqual(sc['banner'], 'عنوان'); self.assertNotIn('bannerOut', sc)

    def test_the_banner_leaves_before_a_late_card(self):
        sc = scene('Breguet · 1991', {'type': 'card', 'in': {'type': 'drop', 'at': 4.1}})
        textload.budget(sc)
        self.assertEqual(sc['banner'], 'Breguet · 1991')
        self.assertAlmostEqual(sc['bannerOut'], 3.8)

    def test_an_early_line_takes_the_banner_s_place(self):
        sc = scene('Max Büsser', {'type': 'text', 'text': 'أسّس بعدها شركته MB&F', 'size': 40, 'in': {'at': 1.0}})
        textload.budget(sc)
        self.assertIsNone(sc['banner']); self.assertNotIn('bannerOut', sc)

    def test_a_card_from_the_start_means_no_banner(self):
        sc = scene('عنوان', {'type': 'card'})
        textload.budget(sc)
        self.assertIsNone(sc['banner'])

    def test_the_end_card_is_left_alone(self):
        end = {'endcard': 'timekeeper', 'banner': 'x', 'elements': [{'type': 'card'}]}
        self.assertEqual(textload.fit([end]), [])
        self.assertEqual(end['banner'], 'x')

    def test_the_engine_moves_the_banner_out(self):
        self.assertIn('bannerOut', (engine.ENGINE / 'engine/paper.js').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
