"""Rule 9e, the news group's house style: names written in Arabic, said in their own language; the house words."""
from tests import _guard  # noqa: F401
import tempfile, unittest
from pathlib import Path

import yaml

from director import brand as B, quickfilm


def film(text, **kw):
    return {'brand': 'timekeeper', 'lines': [{'id': 'l1', 'text': text, 'template': 'kinetic_type', 'params': {}, 'no_photo': 'test', **kw}]}


def check(f):
    return [m for m in quickfilm.story_check(f) if 'as digits' not in m]


class HouseStyle(unittest.TestCase):
    def test_on_for_the_brand_off_for_a_film_made_before(self):
        self.assertTrue(quickfilm.house(film('x')))
        self.assertFalse(quickfilm.house({**film('x'), 'house_style': False}))

    def test_the_voice_gets_the_names_in_their_own_language(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'f.yaml'
            p.write_text(yaml.safe_dump({**film('بيعت في مزاد فيليبس في جنيف وصنع لشركات مثل بريغيه'),
                                         'names': {'فياني هالتر': 'Vianney Halter'}}, allow_unicode=True), encoding='utf-8')
            f = quickfilm.load(p)
            self.assertEqual(f['lines'][0]['text'], 'بيعت في مزاد فيليبس في جنيف وصنع لشركات مثل بريغيه')   # the screen
            self.assertEqual(f['lines'][0]['say'], 'بيعت في مزاد Phillips في Geneva وصنع لشركات مثل Breguet')  # the voice
            self.assertEqual(quickfilm.voice_script(f)[0]['text'], f['lines'][0]['say'])

    def test_a_joined_letter_stays(self):
        self.assertEqual(B.to_voice('وفيليبس ولبريغيه', B.names()), 'و Phillips ول Breguet')

    def test_latin_names_on_screen_are_caught(self):
        out = check(film('بيعت في مزاد Phillips', banner='Breguet · 1991'))
        self.assertTrue(any('«Phillips» on screen in Arabic' in o and 'فيليبس' in o for o in out))
        self.assertTrue(any('«Breguet» on screen in Arabic' in o for o in out))
        self.assertFalse(any('in English letters' in o for o in check(film('فازت في جنيف'))))   # a city in Arabic is fine now

    def test_house_words(self):
        out = check(film('قالب من الفولاذ وذهب وردي'))
        self.assertTrue(any('ستيل' in o for o in out))
        self.assertTrue(any('ذهب احمر' in o for o in out))
        self.assertTrue(any('tanween' in o for o in check(film('ساعة تحمل إطاراً مميزاً'))))
        self.assertFalse([o for o in check(film('ساعة من صانع ما يعرفه الكثير بيعت في مزاد فيليبس')) if 'news' in o])


if __name__ == '__main__':
    unittest.main()
