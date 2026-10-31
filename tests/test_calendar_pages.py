from tests import _guard  # noqa: F401
import random, unittest

from director.studio import sets


class TestCalendarPages(unittest.TestCase):
    def test_a_page_shows_only_once_the_page_above_falls(self):
        els = [e for e in sets.waiting_years(6, random.Random(0))['elements'] if '>20' in e.get('svg', '') and 'font-size="46"' in e['svg']]
        self.assertEqual(len(els), 8)
        top = [e for e in els if '>2003<' in e['svg']][0]
        self.assertNotIn('opacity', top)                                  # 2003 is seen from the start
        for e in els:
            if e is not top: self.assertEqual(e['opacity'][0], [0, 0])      # the rest wait their turn


if __name__ == '__main__':
    unittest.main()
