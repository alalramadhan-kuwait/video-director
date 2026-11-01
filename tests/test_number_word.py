from tests import _guard  # noqa: F401
import unittest

from director.studio import checks


class TestNumberIsOneWord(unittest.TestCase):
    def test_thousands_stay_together(self):
        self.assertEqual(checks.words('بحوالي 71,400 دينار'), ['بحوالي', '71,400', 'دينار'])

    def test_years_and_decimals(self):
        self.assertEqual(checks.words('في 1998 و3.5 ملم'), ['في', '1998', 'و', '3.5', 'ملم'])


    def test_accented_latin_names_stay_whole(self):
        self.assertIn('Büsser', checks.words('وكان Max Büsser مدير'))
        self.assertIn('Antérieur', checks.words('Futur Antérieur'))


if __name__ == '__main__':
    unittest.main()
