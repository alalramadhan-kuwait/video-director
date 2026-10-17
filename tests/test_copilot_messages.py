"""Plain-language messages for the Co-Pilot page (UX stage 1, P3): every refusal the page can receive has an Arabic
sentence with no internal ids, the English reason the rules produce is unchanged, and the page is told where the fix is."""
from tests import _guard  # noqa: F401
import os, re, tempfile, unittest
from pathlib import Path

os.environ['VD_DRAFT_VOICE'] = 'offline-mock'
os.environ['VD_COPILOT_MANUAL_STEP'] = '1'
from director.copilot import messages as M, api as CA

ROOT = Path(__file__).resolve().parents[1]
IDS = re.compile(r'q-tk-|\btk-[a-z0-9]+-|\b[a-z]+_[a-z_]+\b')          # take/flag ids and snake_case codes


class TestMessages(unittest.TestCase):
    def test_every_refusal_the_page_can_receive_has_plain_words(self):
        src = (ROOT / 'director/copilot/actions.py').read_text() + (ROOT / 'director/copilot/api.py').read_text()
        lits = re.findall(r"(?:_refused|Refused)\((f?)(['\"])(.*?)(?<!\\)\2", src)
        self.assertGreater(len(lits), 80)
        missing = []
        for f, _, text in lits:
            text = text.replace("\\'", "'")
            examples = [re.sub(r'\{[^}]*\}', v, text) if f else text for v in ('3', 'l3', 'G2')]
            examples = [e + 'l3' if e.endswith(': ') else e for e in examples]
            if not any(M.explain(e)['known'] for e in examples): missing.append(text)
        self.assertEqual(missing, [])

    def test_no_internal_ids_reach_the_owner(self):
        cases = ['confirm the uncertain words first: q-tk-h-dac23184-w1, q-tk-h-dac23184-w2, q-tk-l2-4ea085f9-w15',
                 'listen to every changed line before approving: h, l5',
                 'critical fact-check result on l3, l9: fix the line, or override it with evidence for THIS line and a sentence saying why '
                 '(l3: cite c4, c5 or a source link; l9: no research claim is linked to it, so cite a source link)',
                 'confirm you have read the warnings on l2, l12', 'scenes changed since this film was made: l6, l9',
                 'not authorized: script v3 is not approved; 2 review finding(s) open; paid generation is disabled in this environment (VIDEO_DIRECTOR_PAID_ENABLED is not 1)']
        for c in cases:
            x = M.explain(c)
            self.assertTrue(x['known'], c)
            self.assertIsNone(IDS.search(x['ar']), (c, x['ar']))
        x = M.explain(cases[0])
        self.assertIn('3 كلمة', x['ar']); self.assertEqual(x['fix']['target'], '#ackqa'); self.assertEqual(x['fix']['panel'], 'g3')
        self.assertIn('السطر 3', M.explain(cases[2])['ar']); self.assertIn('c4', M.explain(cases[2])['ar'])   # the ids you must cite stay
        self.assertIn('الافتتاحية', M.explain(cases[1])['ar'])

    def test_unknown_reason_is_said_plainly_and_kept_as_details(self):
        x = M.explain('some brand new rule nobody translated yet')
        self.assertFalse(x['known']); self.assertEqual(x['ar'], 'تعذّر تنفيذ هذا الطلب.')

    def test_blockers_why_and_titles(self):
        self.assertEqual(M.blocker_ar('script v3 is not approved'), 'النص v3 غير موافق عليه')
        self.assertIn('الصوت', M.why_ar('depends on G2, G3, which is no longer approved'))
        self.assertEqual(M.title_ar('Scene h: a problem the Co-Pilot cannot fix safely'), 'الافتتاحية: مشكلة لا يستطيع المساعد إصلاحها بأمان')
        self.assertEqual(M.title_ar('Scene l7: still not right after 2 correction round(s)'), 'المشهد 7: ما زال غير مضبوط بعد 2 جولة تصحيح')


class TestRefusalResponse(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.var = Path(self.tmp.name)
        code, r = CA.handle(self.var, {'action': 'create', 'args': {'title': 'T', 'idea': 'How the Rolex Oyster (1926) made a waterproof watch people trusted',
                                                                    'brand': 'timekeeper', 'mode': 'copilot'}})
        self.pid = r['project']

    def tearDown(self):
        for p in self.var.rglob('*'):
            if p.is_file(): os.chmod(p, 0o644)
        self.tmp.cleanup()

    def test_the_rule_is_unchanged_and_the_page_gets_plain_words_and_the_fix(self):
        code, r = CA.handle(self.var, {'project': self.pid, 'action': 'cp_gate', 'args': {'gate': 'G1', 'decision': 'changes_requested', 'note': ''}})
        self.assertEqual(code, 422)
        self.assertTrue(r['reason'].isascii())                         # the rule's own (English) reason is still returned as it was
        self.assertTrue(r['reason_ar'] and r['known']); self.assertNotIn('G1', r['reason_ar'])
        code, r = CA.handle(self.var, {'action': 'create', 'args': {'title': 'x', 'idea': '', 'brand': 'timekeeper', 'mode': 'copilot'}})
        self.assertEqual((code, r['reason_ar'], r['fix']['target']), (422, 'اكتب الفكرة أولًا.', '#n-idea'))

    def test_view_names_locked_stages_and_exceptions_in_arabic(self):
        v = CA.view(self.var, self.pid)
        st = {s['id']: s for s in v['stages']}
        self.assertTrue(st['export']['locked']); self.assertTrue(st['export']['why_ar'])
        self.assertFalse(st['direction']['locked'])
