"""The voice gate (the owner, 10 Nov 2026: «there should be a gateway where if the rules are not applied it will not
record»): tools/record_flow.py stops before anything is paid for, with no override for the spoken text."""
from tests import _guard  # noqa: F401
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from director import voice_gate
from tools import record_flow


class Spoken(unittest.TestCase):
    def test_digits_never_reach_the_voice(self):
        p = voice_gate.spoken_problems(['تروح وترد 8 دقات… 28,800 دقة بالساعة'])
        self.assertTrue(any('digits' in x for x in p))
        self.assertEqual(voice_gate.spoken_problems(['ثمانية وعشرين ألف وثمانمية دقة بالساعة']), [])

    def test_english_terms_are_written_in_arabic_letters(self):
        self.assertTrue(voice_gate.spoken_problems(['نلف Mainspring داخل Barrel']))
        self.assertEqual(voice_gate.spoken_problems(['نلف المين سبرينغ داخل الباريل']), [])

    def test_words_the_owner_cleared_by_ear_and_names_pass(self):
        self.assertEqual(voice_gate.spoken_problems(['ساعة Oyster']), [])
        self.assertEqual(voice_gate.spoken_problems(['بيعت في مزاد Phillips'], names=['Phillips']), [])
        self.assertTrue(voice_gate.spoken_problems(['بيعت في مزاد Phillips']))

    def test_article_before_english_and_gaf(self):
        self.assertTrue(any('«ال»' in x for x in voice_gate.spoken_problems(['نلف الـ Mainspring'])))
        self.assertTrue(any('گ' in x for x in voice_gate.spoken_problems(['تگطع'])))


class Screen(unittest.TestCase):
    def test_screen_words_are_arabic_digits_stay(self):
        self.assertTrue(voice_gate.screen_problems([{'text': 'نلف الزنبرك', 'screen': '1 · MAINSPRING'}]))
        self.assertTrue(voice_gate.screen_problems([{'text': 'نلف الـ Mainspring', 'screen': ''}]))
        self.assertEqual(voice_gate.screen_problems([{'text': 'نلف المين سبرينغ', 'screen': '1 · مين سبرينغ · 28,800'}]), [])


class Recording(unittest.TestCase):
    def run_flow(self, lines, *extra, **top):
        d = Path(tempfile.mkdtemp())
        (d / 's.json').write_text(json.dumps({'lines': lines, 'kw_ok': top.get('kw_ok', []), 'rules_ok': top.get('rules_ok', []),
                                              **({'names': top['names']} if 'names' in top else {})},
                                             ensure_ascii=False), encoding='utf-8')
        with mock.patch.object(record_flow, 'speak', side_effect=RuntimeError('PAID')) as sp:
            try:
                rc = record_flow.main([str(d / 's.json'), str(d / 'v'), '--voice', 'x', *extra])
            except RuntimeError as e:
                rc = str(e)
        gate = json.loads((d / 'v' / 'gate.json').read_text(encoding='utf-8')) if (d / 'v' / 'gate.json').exists() else None
        return rc, sp.called, gate

    def test_a_broken_script_is_never_recorded(self):
        rc, paid, gate = self.run_flow([{'n': 1, 'text': 'ساعة بدون بطارية', 'say': 'ساعة فيها 8 دقات'}],
                                       kw_ok=['ساعة', 'بدون', 'بطارية', 'فيها', 'دقات'])
        self.assertEqual(rc, 5); self.assertFalse(paid); self.assertFalse(gate['passed'])

    def test_english_on_screen_stops_it_too(self):
        rc, paid, _ = self.run_flow([{'n': 1, 'text': 'ساعة بدون بطارية', 'screen': 'NO BATTERY'}], kw_ok=['ساعة', 'بدون', 'بطارية'])
        self.assertEqual(rc, 5); self.assertFalse(paid)

    def test_overrides_need_the_owners_words(self):
        rc, paid, _ = self.run_flow([{'n': 1, 'text': 'ساعة بدون بطارية'}], '--rules-ok')
        self.assertEqual(rc, 6); self.assertFalse(paid)

    def test_a_clean_script_reaches_the_voice(self):
        rc, paid, gate = self.run_flow([{'n': 1, 'text': 'ساعة بدون بطارية'}], kw_ok=['ساعة', 'بدون', 'بطارية'])
        self.assertEqual(rc, 'PAID'); self.assertTrue(paid); self.assertTrue(gate['passed'])

    # 11 Nov 2026: the gate stopped a take on «Trieste» in the script text although the film named it in `names`
    TRIESTE = [{'n': 1, 'text': 'غواصة Trieste نزلت', 'say': 'غواصة تريستي نزلت'}]
    KW = ['غواصة', 'تريستي', 'نزلت', 'Trieste']

    def test_a_films_own_name_may_stay_in_latin_in_the_script(self):
        rc, paid, gate = self.run_flow(self.TRIESTE, kw_ok=self.KW)
        self.assertEqual(rc, 5); self.assertFalse(paid)                       # not named: rule 16 still stops it
        self.assertTrue(any('script' in p and 'Trieste' in p for p in gate['problems']))
        for names in ({'Trieste': 'تريستي'}, ['Trieste'], {'تريستي': 'Trieste'}):   # the name → Arabic, a list, Arabic → the name
            rc, paid, gate = self.run_flow(self.TRIESTE, kw_ok=self.KW, names=names)
            self.assertEqual((rc, paid, gate['problems']), ('PAID', True, []), names)

    def test_a_films_own_name_on_screen_too_and_only_that_name(self):
        lines = [{**self.TRIESTE[0], 'screen': 'Trieste · 1960'}]
        self.assertEqual(self.run_flow(lines, kw_ok=self.KW, names=['Trieste'])[0], 'PAID')
        rc, paid, gate = self.run_flow([{**self.TRIESTE[0], 'screen': 'Trieste DEEP'}], kw_ok=self.KW, names=['Trieste'])
        self.assertEqual(rc, 5); self.assertFalse(paid); self.assertTrue(any('DEEP' in p for p in gate['problems']))

    def test_the_voice_still_gets_the_name_in_arabic(self):
        # without `say`, the Latin name would reach the voice: a list or a name → Arabic pair does not clear that
        for names in (['Trieste'], {'Trieste': 'تريستي'}):
            rc, paid, gate = self.run_flow([{'n': 1, 'text': 'غواصة Trieste نزلت'}], kw_ok=self.KW, names=names)
            self.assertEqual(rc, 5); self.assertFalse(paid)
            self.assertEqual([p for p in gate['problems'] if '(script)' in p or '(screen)' in p], [])
            self.assertTrue(any('(voice)' in p and 'Trieste' in p for p in gate['problems']))


class FilmNames(unittest.TestCase):
    def test_names_as_a_list_or_pairs_either_way(self):
        from director import quickfilm
        self.assertEqual(quickfilm.script_names({'names': ['Trieste', 'Jacques Piccard']}), ['Trieste', 'Jacques Piccard'])
        self.assertEqual(quickfilm.script_names({'names': {'Trieste': 'تريستي'}}), ['Trieste'])
        self.assertEqual(quickfilm.script_names({'names': {'تريستي': 'Trieste'}}), ['Trieste'])
        self.assertEqual(quickfilm.script_names({}), [])
        # a list used to crash («'list' object is not a mapping»); a name → Arabic pair never enters the said-as table
        self.assertNotIn('Trieste', quickfilm.house_names({'names': ['Trieste']}))
        self.assertNotIn('Trieste', quickfilm.house_names({'names': {'Trieste': 'تريستي'}}))
        self.assertEqual(quickfilm.house_names({'names': {'تريستي': 'Trieste'}})['تريستي'], 'Trieste')


if __name__ == '__main__':
    unittest.main()
