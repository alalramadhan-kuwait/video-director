"""The owner: «I want you to understand every change I'm doing in the carousel so it can be updated for the future, to
keep it as a reference and learn from it». Each edit is kept word for word (the studio, and tools/carousel/edits.py
for the log in references/carousel-edits.md)."""
from tests import _guard  # noqa: F401
import importlib.util, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('edits', ROOT / 'tools/carousel/edits.py')
edits = importlib.util.module_from_spec(spec); spec.loader.exec_module(edits)

WAS = 'أبوه كان يشتغل على القطارات، ويجيب للبيت قطع من مكاين قديمة'
NOW = 'أبوه كان يشتغل على القطارات، يحضر للبيت قطع من محركات قديمة'


def sp(body):
    return {'cover': {'top': 'ساعة', 'bottom': 'لصانع'}, 'slides': [{'title': 'ولد التروس', 'body': f'<b>باريس</b> {body}'}, {'title': 'ب', 'body': 'ج'}]}


class Edits(unittest.TestCase):
    def test_the_changed_words_only(self):
        self.assertEqual(edits.wdiff(WAS, NOW), [('ويجيب', 'يحضر'), ('مكاين', 'محركات')])
        self.assertEqual(edits.wdiff('a b c', 'a c d'), [('b', ''), ('', 'd')])

    def test_field_by_field(self):
        d = edits.diff(sp(WAS), sp(NOW), 'كابشن', 'كابشن')
        self.assertEqual([(x['where'], x['key']) for x in d], [('الشريحة 1', 'body')])
        self.assertTrue(d[0]['before'].startswith('**باريس**'))
        self.assertEqual(edits.diff(sp(WAS), sp(WAS), 'a', 'b')[0]['key'], 'caption')

    def test_an_older_save_is_found_from_history(self):
        rec = {'name': 'Halter · 1', 'version': 'v6', 'edited': 'studio', 'spec': sp(NOW), 'caption': 'x',
               'history': [{'version': 'v5', 'spec': sp(WAS), 'caption': 'x', 'at': '2026-11-02T15:34:03Z'}],
               'changes': [{'v': 'v6', 'at': '2026-11-02T15:34:03Z', 'what': ['عدّلت النص بنفسك: الشريحة 1']}]}
        out = edits.owner_edits(rec)
        self.assertEqual(len(out), 1); self.assertEqual(out[0]['version'], 'v6')
        self.assertIn('«مكاين» ← «محركات»', edits.entry(out[0]))
        # a later version of mine (bigger text, same words) on top does not hide it, nor count as the owner's
        rec2 = dict(rec, version='v7', history=[{'version': 'v6', 'spec': sp(NOW), 'caption': 'x'}] + rec['history'],
                    changes=[{'v': 'v7', 'at': 'z', 'what': ['الخط أكبر']}] + rec['changes'])
        self.assertEqual([e['version'] for e in edits.owner_edits(rec2)], ['v6'])

    def test_a_new_save_carries_its_edits_and_why(self):
        e = [{'where': 'الغلاف', 'field': 'السطر الأول', 'key': 'top', 'before': 'أ', 'after': 'ب'}]
        rec = {'name': 'X', 'version': 'v2', 'edited': 'studio', 'changes': [{'v': 'v2', 'at': '2026-11-03', 'edits': e, 'why': 'أوضح'}]}
        out = edits.owner_edits(rec)
        self.assertEqual(len(out), 1); self.assertIn('أوضح', edits.entry(out[0]))

    def test_the_studio_keeps_them(self):
        page = (ROOT / 'studio-page/index.html').read_text(encoding='utf-8')
        for s in ('function edDiff', 'function wdiff', "data-ef=\"why\"", 'edits, ...(why'):
            self.assertIn(s, page)
