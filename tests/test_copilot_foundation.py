"""Foundation: one mode rule on the server for every action, a safe way back from Manual to the Co-Pilot,
the Classic link, and the shared cost data. Nothing here may approve around a gate or start paid work."""
from tests import _guard  # noqa: F401
import os, unittest
from pathlib import Path

from tests.test_copilot import Env, run_step, IDEA
from director.studio.store import Refused
from director.studio import api as SA
from director.copilot import api as CA, approvals as A, orchestrator as O


class TestModeRule(Env):
    def manual(self):
        self.owner('cp_mode', {'mode': 'manual'})

    def test_copilot_decisions_never_change_a_manual_or_classic_project(self):
        self.to_g2(); self.manual()
        sv = self.S.state(self.pid)['scripts'][-1]['v']
        for action, args in (('cp_gate', {'gate': 'G2', 'decision': 'approved', 'content_hash': A.current(self.S.state(self.pid))['G2']['hash']}),
                             ('cp_hook', {'hook': 'H3'}), ('cp_line_edit', {'line': 'l3', 'text': 'جملة'}), ('cp_comment', {'film': 1, 't': 1, 'text': 'x'})):
            with self.assertRaises(Refused, msg=action) as e: self.owner(action, args)
            self.assertIn('Manual', str(e.exception))
        # the Co-Pilot itself (a job still running when you switched) cannot record its work either
        with self.assertRaises(Refused): self.S.act(self.pid, 'cp_stage', {'key': 'x', 'stage': 'script', 'state': 'done'}, actor='copilot')
        # ... but what an AI call cost is always recorded
        self.S.act(self.pid, 'cp_ai_call', {'id': 'ai-z', 'kind': 'fact_check', 'role': 'r', 'worker': 'mock', 'label': 'x', 'state': 'done', 'cost_usd': 0.0}, actor='system')
        # a classic project (created in the classic Studio) is never changed by the Co-Pilot
        code, r = SA.handle(self.var, {'action': 'create_project', 'args': {'title': 'Classic one', 'idea': IDEA, 'brand': 'timekeeper'}})
        cid = r['project']
        with self.assertRaises(Refused) as e: self.S.act(cid, 'cp_hook', {'hook': 'H1'})
        self.assertIn('classic', str(e.exception))
        self.S.act(cid, 'research', {'data': {'claims': [{'id': 'c1', 'text': 'x', 'status': 'verified', 'sources': ['https://example.org/a']}]}}, 'research')
        with self.assertRaises(Refused) as e: self.S.act(cid, 'cp_mode', {'mode': 'copilot'}, actor='owner')   # once it has work, it stays classic
        self.assertIn('classic', str(e.exception))
        self.assertEqual(self.S.state(self.pid)['scripts'][-1]['v'], sv)

    def test_classic_decisions_cannot_go_around_a_copilot_gate(self):
        self.to_g2()
        v = self.S.state(self.pid)['scripts'][-1]['v']
        for action, args in (('script_decision', {'v': v, 'decision': 'approved', 'note': 'x'}), ('hook_select', {'hook': 'H2'}), ('set_budget', {'chars': 5000})):
            with self.assertRaises(Refused, msg=action): self.S.act(self.pid, action, args, actor='owner')       # any caller, not only the classic page
        self.gate('G2')                                                     # the gate itself still records the script decision inside it
        self.assertEqual(self.S.state(self.pid)['scripts'][-1]['status'], 'approved')

    def test_manual_decisions_are_not_turned_into_approvals_and_are_shown_before_going_back(self):
        self.to_g2(); self.manual()
        v = self.S.state(self.pid)['scripts'][-1]['v']
        code, r = SA.handle(self.var, {'project': self.pid, 'action': 'script_decision', 'args': {'v': v, 'decision': 'approved', 'note': 'by hand'}})
        self.assertEqual(code, 200, r)
        view = CA.view(self.var, self.pid)
        b = view['back']
        self.assertTrue(any(m['what_ar'] == 'النص' and m['decision'] == 'approved' for m in b['made']), b['made'])
        self.assertTrue(any(o['gate_ar'] == 'النص والافتتاحية' for o in b['open_ar']), b['open_ar'])
        self.assertFalse(view['validity']['G2']['valid'])                  # approved by hand, but not a Co-Pilot approval
        self.assertEqual(O.plan(self.S, self.pid)['step'], None)            # nothing runs while in Manual
        self.assertTrue(b['paid_locked']); self.assertFalse(b['ai_real'])
        # going back (with resume): the gate still waits for you; the approval is confirmed only by you
        code, r = CA.handle(self.var, {'project': self.pid, 'action': 'cp_mode', 'args': {'mode': 'copilot', 'resume': True}})
        self.assertEqual(code, 200, r)
        st = self.S.state(self.pid)
        self.assertEqual((st['copilot']['mode'], st['copilot']['run']), ('copilot', 'running'))
        self.assertFalse(A.validity(st)['G2']['valid'])
        self.assertIn('G2', O.plan(self.S, self.pid)['waiting'])
        self.gate('G2')                                                     # confirming an already approved script (audit D7)
        self.assertTrue(A.validity(self.S.state(self.pid))['G2']['valid'])

    def test_one_decision_wins_and_paid_work_cannot_start_from_either_side(self):
        self.to_g2(); self.gate('G2')
        self.manual()
        v = self.S.state(self.pid)['scripts'][-1]['v']
        code, r = SA.handle(self.var, {'project': self.pid, 'action': 'script_decision', 'args': {'v': v, 'decision': 'rejected', 'note': 'x'}})
        self.assertEqual(code, 422); self.assertIn('already approved', r['reason'])
        for route, action, args in ((SA, 'gate_authorize', {'confirm_text': '1'}), (SA, 'final_generate', {}), (CA, 'cp_gate', {'gate': 'G6', 'decision': 'approved'})):
            code, r = route.handle(self.var, {'project': self.pid, 'action': action, 'args': args})
            self.assertEqual(code, 422, (action, r))
        self.assertEqual(self.S.state(self.pid)['copilot']['ai']['spent_usd'], 0.0)

    def test_switching_to_manual_while_working_stops_the_drawing(self):
        killed = []
        orig = CA.kill_renders
        CA.kill_renders = lambda S, pid: killed.append(pid) or 0
        try:
            code, r = CA.handle(self.var, {'project': self.pid, 'action': 'cp_mode', 'args': {'mode': 'manual'}})
        finally:
            CA.kill_renders = orig
        self.assertEqual((code, killed), (200, [self.pid]))

    def test_links_and_shared_cost_data(self):
        self.assertEqual(CA.view(self.var, self.pid)['classic_url'], f'/studio/classic#/p/{self.pid}/')
        page = (Path(__file__).resolve().parents[1] / 'director/copilot/copilot.html').read_text()
        self.assertNotIn("'/studio/classic#' + encodeURIComponent", page)
        from director.dashboard import snapshot
        old = os.environ.get('VD_DASHBOARD_VAR')
        os.environ['VD_DASHBOARD_VAR'] = str(self.var)
        try:
            self.assertEqual(snapshot._var(), self.var)
        finally:
            if old is None: os.environ.pop('VD_DASHBOARD_VAR')
            else: os.environ['VD_DASHBOARD_VAR'] = old


class TestRecommendation(unittest.TestCase):
    """A choice is highlighted only with a clear reason, and never for a scene whose best version still has a real problem."""
    def test_only_with_a_clear_reason(self):
        cp = {'scenes': {'l3': {'versions': [{'n': 2, 'findings': [{'severity': 'minor'}, {'severity': 'info'}]}]},
                         'l4': {'versions': [{'n': 1, 'findings': [{'severity': 'major'}]}]}}}
        ex = lambda **k: {'status': 'open', **k}
        self.assertEqual(CA._recommend(cp, ex(kind='rights', options=['keep_fallback']))['option'], 'keep_fallback')
        self.assertEqual(CA._recommend(cp, ex(kind='fact', options=['remove_banner', 'manual']))['option'], 'remove_banner')
        r = CA._recommend(cp, ex(kind='retry_limit', scene='l3', version=2, options=['accept_best', 'retry_with_change', 'manual']))
        self.assertEqual(r['option'], 'accept_best'); self.assertTrue(r['why_ar'])
        self.assertIsNone(CA._recommend(cp, ex(kind='retry_limit', scene='l4', version=1, options=['accept_best', 'retry_with_change', 'manual'])))
        self.assertIsNone(CA._recommend(cp, ex(kind='comment', options=['manual', 'dismiss_comment'])))
        self.assertIsNone(CA._recommend(cp, {**ex(kind='rights', options=['keep_fallback']), 'status': 'resolved'}))
