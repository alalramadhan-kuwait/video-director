from tests import _guard  # noqa: F401
import unittest

from director import quickfilm


def check(text):
    lines = [{'id': 'a', 'text': text, 'template': 'kinetic_type', 'params': {}, 'no_photo': 'test'}]
    return [m for m in quickfilm.story_check({'lines': lines, 'house_style': False}) if 'English letters' in m]   # before rule 9e


class TestForeignPlaces(unittest.TestCase):
    def test_a_foreign_city_in_arabic_letters_is_caught(self):
        self.assertTrue(check('فازت بجائزة جنيف الكبرى للساعات.'))
        self.assertTrue(check('ثم عاد إلى باريس.'))

    def test_latin_and_arab_places_pass(self):
        self.assertEqual(check('فازت بجائزة Geneva الكبرى للساعات.'), [])
        self.assertEqual(check('وُلد في الكويت.'), [])


if __name__ == '__main__':
    unittest.main()
