from tests import _guard  # noqa: F401
import unittest

from director import quickfilm


def flags(banner, text='ساعة صنعها فريق كبير.'):
    lines = [{'id': 'a', 'text': text, 'template': 'kinetic_type', 'params': {}, 'no_photo': 'test', 'banner': banner, 'screen_ok': True}]
    return [m for m in quickfilm.story_check({'lines': lines}) if 'never explained' in m]


class TestUnexplainedTerms(unittest.TestCase):
    def test_an_unexplained_abbreviation_is_flagged_even_with_screen_ok(self):
        self.assertTrue(flags('Breguet · فريق THA'))

    def test_explained_or_said_passes(self):
        self.assertEqual(flags('أسّس بعدها شركته MB&F'), [])
        self.assertEqual(flags('THA · 1991', text='اشتغل في ورشة THA.'), [])


if __name__ == '__main__':
    unittest.main()
