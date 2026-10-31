from tests import _guard  # noqa: F401
import unittest

from director import quickfilm


class TestAppear(unittest.TestCase):
    def test_the_print_waits_for_its_word(self):
        sc = {'elements': [{'type': 'photo', 'in': {'type': 'drop', 'at': .15}},
                           {'type': 'card', 'in': {'type': 'drop', 'at': .6}}, {'type': 'text', 'z': 40, 'in': {'type': 'fade', 'at': .3}}]}
        words = [{'w': 'Basel', 's': 3.0}, {'w': 'Antiqua', 's': 5.0}]
        self.assertEqual(quickfilm.line_appear(sc, {'id': 'l5', 'appear': {'on': 'Antiqua'}}, words, 8.0), [])
        t = quickfilm.VOICE_AT + 5.0
        self.assertAlmostEqual(sc['elements'][0]['in']['at'], t, delta=.01)
        self.assertGreater(sc['elements'][1]['in']['at'], t); self.assertGreater(sc['elements'][2]['in']['at'], t)
        self.assertEqual(sc['sfx'][0]['name'], 'shutter')

    def test_no_word_no_change(self):
        sc = {'elements': [{'type': 'photo'}]}
        self.assertTrue(quickfilm.line_appear(sc, {'id': 'x', 'appear': 'Nope'}, [], 4.0))


if __name__ == '__main__':
    unittest.main()
