from tests import _guard  # noqa: F401
import unittest

from director import quickfilm


class TestReveal(unittest.TestCase):
    def test_a_print_is_unveiled_on_its_word(self):
        sc = {'elements': [{'type': 'photo', 'asset': 'w', 'w': 400, 'aspect': .8, 'x': 360, 'y': 520}]}
        words = [{'w': 'في', 's': 0.2}, {'w': 'Basel', 's': 1.0}, {'w': 'Antiqua', 's': 2.0}]
        self.assertEqual(quickfilm.line_reveal(sc, {'id': 'l5', 'reveal': {'on': 'Antiqua'}}, words, 4.0), [])
        cloth = sc['elements'][-1]
        self.assertEqual(cloth['type'], 'svg'); self.assertNotIn('dial', cloth['svg'])
        self.assertGreater(cloth['w'], 400); self.assertGreater(cloth['z'], 0)
        ys = cloth['y']
        self.assertEqual(ys[0], [0, 520])                                    # over the print from the first frame
        self.assertLess(ys[-1][1], -500)                                     # pulled away, out of the frame
        self.assertAlmostEqual(ys[-1][0] - .7, quickfilm.VOICE_AT + 2.0, delta=.05)
        self.assertTrue(any(c['name'] == 'whoosh' for c in sc['sfx']))

    def test_no_print_no_reveal(self):
        sc = {'elements': []}
        self.assertTrue(quickfilm.line_reveal(sc, {'id': 'l5', 'reveal': 'Antiqua'}, [{'w': 'Antiqua', 's': 1.0}], 4.0))


if __name__ == '__main__':
    unittest.main()
