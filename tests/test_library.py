from tests import _guard  # noqa: F401
import os, tempfile, unittest
from director.library import Library, Entry, bare
from director import importers
from tests.fixtures import RO, DH_LEXICON


def lib(*entries):
    return Library(list(entries))

STEEL = Entry(id='steel', scope='brand:timekeeper', surface='ستيل', status='approved',
              providers={'elevenlabs': {'mode': 'spoken', 'spoken': 'Steel'}, 'habibi': {'mode': 'spoken', 'spoken': 'Steel'},
                         'fasih': {'mode': 'stem', 'stem': 'سْتِيل'}})
QUARTZ_KEEP = Entry(id='quartz-keep', scope='brand:timekeeper', surface='كوارتز', status='approved',
                    providers={'elevenlabs': {'mode': 'keep_arabic'}})
GENTA = Entry(id='genta', scope='brand:timekeeper', surface='جنتا', status='approved', providers={'elevenlabs': {'mode': 'spoken', 'spoken': 'Genta'}})
GERALD_GENTA = Entry(id='gerald-genta', scope='brand:timekeeper', surface='جيرالد جنتا', status='approved',
                     providers={'elevenlabs': {'mode': 'spoken', 'spoken': 'Gérald Genta'}})


class TestMatching(unittest.TestCase):
    def test_article_and_prefixes_are_recognised(self):
        L = lib(STEEL)
        for text, prefix, art in [('الستيل', 'ال', True), ('بالستيل', 'بال', True), ('والستيل', 'وال', True),
                                  ('للستيل', 'لل', True), ('ستيل', '', False), ('وستيل', 'و', False)]:
            m = L.find(text)
            self.assertEqual(len(m), 1, text)
            self.assertEqual(bare(m[0].prefix), prefix, text)
            self.assertEqual(m[0].has_article, art, text)

    def test_diacritics_do_not_break_matching_and_are_preserved_outside(self):
        L = lib(STEEL)
        text = 'مِنَ السْتِيلِ الفَاخِرِ'
        m = L.find(text)
        self.assertEqual(len(m), 1)
        out, _ = L.prepare(text, 'fasih')
        # words outside the match keep their marks; the matched word becomes article + approved stem.
        # Known limit: 'stem' mode does not carry the case ending (arabic_tts stays the authority for Fasih endings).
        self.assertEqual(out, 'مِنَ السْتِيل الفَاخِرِ')

    def test_no_blind_substring_replacement(self):
        L = lib(STEEL)
        self.assertEqual(L.find('ستيلان والستيلات'), [])          # longer words that merely contain the surface

    def test_longest_multiword_wins_and_punctuation_breaks_phrases(self):
        L = lib(GENTA, GERALD_GENTA)
        self.assertEqual(L.prepare('جيرالد جنتا يرسم', 'elevenlabs')[0], 'Gérald Genta يرسم')
        out = L.prepare('جيرالد، جنتا', 'elevenlabs')[0]          # a comma between: not the two-word name
        self.assertEqual(out, 'جيرالد، Genta')

    def test_latin_in_script_is_untouched(self):
        self.assertEqual(lib(STEEL).prepare('Royal Oak من الستيل', 'elevenlabs')[0], 'Royal Oak من Steel')


class TestArticleRule(unittest.TestCase):
    def test_article_dropped_is_flagged_for_latin_respelling(self):
        out, f = lib(STEEL).prepare('ساعة من الستيل', 'elevenlabs', line='p2-1')
        self.assertEqual(out, 'ساعة من Steel')
        self.assertEqual([x.code for x in f], ['ARTICLE_DROPPED'])
        self.assertEqual(f[0].severity, 'major')

    def test_keep_arabic_preserves_article(self):
        out, f = lib(QUARTZ_KEEP).prepare('هدّدت ساعاتُ الكوارتز', 'elevenlabs')
        self.assertEqual(out, 'هدّدت ساعاتُ الكوارتز')
        self.assertEqual(f, [])

    def test_line_override_beats_brand_rule(self):
        line_keep = Entry(id='keep-p2h', scope='project:royal-oak', surface='ستيل', status='approved', lines=['p2-h'],
                          providers={'elevenlabs': {'mode': 'keep_arabic'}})
        L = lib(STEEL, line_keep)
        self.assertEqual(L.prepare('من الستيل', 'elevenlabs', line='p2-h')[0], 'من الستيل')
        self.assertEqual(L.prepare('من الستيل', 'elevenlabs', line='p2-1')[0], 'من Steel')

    def test_unapproved_entries_are_reported_not_applied(self):
        e = Entry(**{**STEEL.__dict__, 'status': 'proposed'})
        out, f = lib(e).prepare('من الستيل', 'elevenlabs')
        self.assertEqual(out, 'من الستيل')
        self.assertEqual(f[0].code, 'UNAPPROVED_ENTRY')


class TestValidationAndScopes(unittest.TestCase):
    def test_validation(self):
        bad = Entry(id='x', scope='brand:tk', surface='الستيل', status='weird',
                    providers={'fasih': {'mode': 'stem', 'stem': 'كُوارْتْز'}})
        errs = Library([bad]).errors
        self.assertTrue(any('without «ال»' in e for e in errs))
        self.assertTrue(any('bad status' in e for e in errs))
        self.assertTrue(any('stem letters differ' in e for e in errs))

    def test_scopes_keep_projects_apart(self):
        with tempfile.TemporaryDirectory() as d:
            Library([STEEL, Entry(id='dh', scope='series:diabetes-history', surface='إنسولين', status='approved',
                                  providers={'fasih': {'mode': 'stem', 'stem': 'إِنْسُولِين'}})]).dump(os.path.join(d, 'all.yaml'))
            tk = Library.load(os.path.join(d, 'all.yaml'), scopes={'brand:timekeeper'})
            dh = Library.load(os.path.join(d, 'all.yaml'), scopes={'series:diabetes-history'})
            self.assertEqual([e.id for e in tk.entries], ['steel'])
            self.assertEqual([e.id for e in dh.entries], ['dh'])

    def test_version_changes_with_content(self):
        a = lib(STEEL).version
        b = lib(Entry(**{**STEEL.__dict__, 'providers': {'elevenlabs': {'mode': 'keep_arabic'}}})).version
        self.assertNotEqual(a, b)


class TestImporters(unittest.TestCase):
    @unittest.skipUnless((RO / 'tts_habibi.py').exists(), 'Royal Oak clone not present')
    def test_habibi_import_does_not_execute_the_module(self):
        side_effect_dir = RO / 'voice-habibi' / 'clips'
        existed = side_effect_dir.exists()
        es = importers.habibi_pron(RO / 'tts_habibi.py')
        self.assertEqual(side_effect_dir.exists(), existed)       # importing it would have created this folder
        self.assertTrue(all(e.status == 'imported' for e in es))
        surf = {e.surface for e in es}
        for s in ('ستيل', 'كوارتز', 'جيرالد جنتا', 'أوديمار بيغيه', 'يونيفرسال جنيف', 'رويال أوك', 'بولروتر', 'بازل'):
            self.assertIn(s, surf, s)
        self.assertEqual(Library(es).errors, [])

    @unittest.skipUnless(DH_LEXICON.exists(), 'diabetes lexicon not present')
    def test_diabetes_lexicon_import_stays_in_its_scope(self):
        es = importers.arabic_tts_lexicon(DH_LEXICON)
        self.assertTrue(es)
        self.assertTrue(all(e.scope == 'series:diabetes-history' and set(e.providers) == {'fasih'} for e in es))


if __name__ == '__main__':
    unittest.main()
