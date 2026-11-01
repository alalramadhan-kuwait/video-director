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

    def test_a_name_before_arabic_punctuation_is_still_said_in_its_language(self):
        self.assertEqual(B.to_voice('وفي ١٧٠٤ بلندن، سجّل', quickfilm.house_names({})), 'وفي ١٧٠٤ ب London، سجّل')

    def test_a_person_introduced_by_their_arabic_name(self):
        f = {**film('سجّل براءة', template='archive_photo', banner='فاتيو دي دولييه · عالم رياضيات', params={'asset': 'fatio'}),
             'names': {'فاتيو دي دولييه': 'Fatio de Duillier'},
             'photos': {'fatio': {'file': 'x.jpg', 'person': 'Nicolas Fatio de Duillier'}}}
        self.assertFalse([o for o in check(f) if 'not introduced' in o])

    def test_a_line_that_continues_the_sentence_needs_no_lead_in(self):
        f = film('ثم رفضوا', closing=False)
        f['lines'].append({'id': 'l2', 'text': 'ليثبتوا أن الفكرة قديمة', 'template': 'kinetic_type', 'params': {}, 'no_photo': 'test', 'continues': True})
        self.assertFalse([o for o in check(f) if 'leading in' in o])

    def test_latin_names_on_screen_are_caught(self):
        out = check(film('بيعت في مزاد Phillips', banner='Breguet · 1991'))
        self.assertTrue(any('«Phillips» on screen in Arabic' in o and 'فيليبس' in o for o in out))
        self.assertTrue(any('«Breguet» on screen in Arabic' in o for o in out))
        self.assertFalse(any('in English letters' in o for o in check(film('فازت في جنيف'))))   # a city in Arabic is fine now

    def test_house_words_only_what_the_news_never_writes(self):
        out = check(film('قالب من الفولاذ مع تعبئة يدوية'))
        self.assertTrue(any('ستيل' in o for o in out))
        self.assertTrue(any('تكويك يدوي' in o for o in out))
        # the published news does write these: no finding (the owner: the final posts are the reference, not the chat)
        self.assertFalse([o for o in check(film('لقد صنعها بالذهب الوردي مع مينا مميزة')) if 'news' in o])
        self.assertFalse([o for o in check(film('ساعة من صانع ما يعرفه الكثير بيعت في مزاد فيليبس')) if 'news' in o])

    def test_the_dictionary_still_decides_how_a_name_is_said(self):
        lex = B.lexicon()
        said = B.spoken(B.to_voice('صنعها لشركة بانيراي', B.names()))   # the screen's Arabic → Latin → the dictionary
        self.assertEqual(said, 'صنعها لشركة ' + lex['Panerai'])


if __name__ == '__main__':
    unittest.main()
