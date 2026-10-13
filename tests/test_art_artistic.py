"""Artistic pass: whatever a model writes, its findings stay recommendations; nothing touches artwork."""
from tests import _guard  # noqa: F401
import hashlib, os, tempfile, unittest
from pathlib import Path
from director.art import artistic as A

PACK = {'video': 'v.mp4', 'contact': 'contact.jpg', 'scenes': [
    {'id': 'b4', 'start': 99.6, 'end': 113.5, 'stills': {'start': 'stills/b4_start.jpg', 'mid': 'stills/b4_mid.jpg', 'end': 'stills/b4_end.jpg'}, 'strip': 'strips/b4.jpg'},
    {'id': 'd5', 'start': 178.0, 'end': 192.2, 'stills': {'mid': 'stills/d5_mid.jpg'}, 'strip': 'strips/d5.jpg'}]}
SCENES = {'b4': {'narration': 'في تورونتو أضاف سكوت وفيشر الزنك', 'plan': 'card «تورونتو · 1936»', 'on_screen_text': ['تورونتو · 1936']}}
FACTS = [{'id': 'F4', 'fact': 'Scott and Fisher added zinc, autumn 1936', 'sources': ['https://example.org']}]
PROFILE = {'id': 'diabetes-history-sci', 'status': 'draft', 'look': {'palette': {'bg': '#1C3550'}}}


def raw(**kw):
    base = {'scene': 'b4', 't': 101, 'dimension': 'accuracy', 'problem': 'card shows 1963', 'severity': 'critical',
            'confidence': 'high', 'claim': 'factual', 'evidence': [{'kind': 'still', 'ref': 'stills/b4_mid.jpg'}],
            'suggestion': 'set the card to 1936'}
    base.update(kw); return base


class TestArtistic(unittest.TestCase):
    def setUp(self):
        self.req = A.build_request(PACK, SCENES, PROFILE, FACTS)
        self.rev = {'kind': 'model', 'context': 'independent'}

    def test_request_carries_evidence_not_technical_results(self):
        self.assertNotIn('technical', self.req)
        self.assertEqual(self.req['scenes'][0]['narration'], SCENES['b4']['narration'])
        self.assertEqual(self.req['scenes'][0]['timecode'], '01:39.6–01:53.5')
        self.assertEqual(set(self.req['dimensions']), set(A.DIMENSIONS))

    def test_ai_output_is_always_a_proposal(self):
        kept, _ = A.accept_ai_findings([raw(status='accepted', source='human', requires_human=False,
                                            evidence=[{'kind': 'still', 'ref': 'stills/b4_mid.jpg'}, {'kind': 'fact', 'ref': 'F4'}])],
                                       self.req, self.rev)
        f = kept[0]
        self.assertEqual((f['source'], f['status'], f['requires_human']), ('ai_judgement', 'proposed', True))
        self.assertEqual(f['severity'], 'critical')                     # cited fact: severity kept
        self.assertEqual(f['timecode'], '01:41.0')

    def test_uncited_factual_claim_is_capped_and_flagged(self):
        kept, _ = A.accept_ai_findings([raw()], self.req, self.rev)
        f = kept[0]
        self.assertEqual((f['severity'], f['confidence']), ('major', 'low'))
        self.assertTrue(any('check the source' in n for n in f['notes']))

    def test_unsupported_findings_are_discarded_with_a_reason(self):
        bad = [raw(scene='zz'), raw(dimension='vibes'), raw(problem=''),
               raw(evidence=[{'kind': 'still', 'ref': 'stills/not_in_packet.jpg'}])]
        kept, dropped = A.accept_ai_findings(bad, self.req, self.rev)
        self.assertEqual(kept, [])
        self.assertEqual([d['reason'].split(' ')[0] for d in dropped], ['unknown', 'unknown', 'no', 'no'])

    def test_time_is_clamped_into_the_scene(self):
        kept, _ = A.accept_ai_findings([raw(t=5000, dimension='composition', claim='aesthetic')], self.req, self.rev)
        self.assertEqual(kept[0]['t'], 113.5)

    def test_report_keeps_the_three_kinds_apart(self):
        ai, dropped = A.accept_ai_findings([raw(dimension='composition', claim='aesthetic', severity='minor')], self.req, self.rev)
        tech = A.from_technical([{'code': 'STATIC_STRETCH', 'severity': 'major', 'scene': 'd5', 't': 180.0,
                                  'detail': 'no change for 3.4 s', 'evidence': {'from': 180, 'to': 183.4}}], PACK)
        rep = A.report(tech, ai, dropped, self.req)
        self.assertEqual(rep['automated'][0]['source'], 'automated')
        self.assertEqual(rep['ai_judgement'][0]['source'], 'ai_judgement')
        self.assertEqual(set(rep['needs_human']), {tech[0]['id'], ai[0]['id']})

    def test_decisions_are_appended_and_never_touch_art(self):
        with tempfile.TemporaryDirectory() as d:
            art = Path(d) / 'b4_mid.jpg'; art.write_bytes(b'\xff\xd8 fake jpeg')
            h = hashlib.sha256(art.read_bytes()).hexdigest()
            log = Path(d) / 'decisions.jsonl'
            with self.assertRaises(ValueError):
                A.decide(log, 'f_x', 'proposed', by='owner')
            A.decide(log, 'f_x', 'needs_source', by='owner'); A.decide(log, 'f_x', 'accepted', by='owner', note='fix the card')
            self.assertEqual(A.current_status(log, 'f_x'), 'accepted')
            self.assertEqual(A.current_status(log, 'f_other'), 'proposed')
            self.assertEqual(len(log.read_text().splitlines()), 2)
            self.assertEqual(hashlib.sha256(art.read_bytes()).hexdigest(), h)
        self.assertFalse(any(n in dir(A) for n in ('apply', 'fix', 'edit', 'repaint', 'modify')))

    def test_blind_scoring(self):
        truth = {'T1': {'defect': True, 'dimensions': ['accuracy'], 'what': 'wrong year'},
                 'T2': {'defect': True, 'dimensions': ['arabic_text'], 'what': 'broken text'},
                 'T3': {'defect': False, 'dimensions': [], 'what': None}}
        f = [{'id': 'a', 'scene': 'T1', 'dimension': 'accuracy', 'severity': 'major'},
             {'id': 'b', 'scene': 'T3', 'dimension': 'style', 'severity': 'major'}]
        s = A.score(f, truth)
        self.assertEqual((s['caught'], s['missed'], s['recall'], s['clean_items_with_major_or_critical']), (1, 1, 0.5, 1))


if __name__ == '__main__':
    unittest.main()
