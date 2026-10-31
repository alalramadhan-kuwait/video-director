from tests import _guard  # noqa: F401
import unittest

from director import quickfilm


def leads(lines):
    lines = [{'template': 'kinetic_type', 'params': {}, 'no_photo': 'test', **ln} for ln in lines]
    return [m for m in quickfilm.story_check({'lines': lines}) if 'leading in' in m]


class TestLeadIn(unittest.TestCase):
    def test_lakinnahu_leads_in(self):
        self.assertEqual(leads([{'id': 'a', 'text': 'ساعة نادرة بيعت في مزاد كبير جدًا.'},
                                {'id': 'b', 'text': 'لكنه صمّم ساعةً أخرى.'}]), [])

    def test_a_pause_in_one_scene_is_not_a_change(self):
        p = {'asset': 'w1'}
        self.assertEqual(leads([{'id': 'a', 'text': 'ساعة بيعت في مزاد كبير.', 'set': 'room', 'params': p},
                                {'id': 'b', 'text': 'ما سرّها؟', 'set': 'room', 'params': p}]), [])

    def test_a_new_scene_still_needs_a_lead(self):
        self.assertTrue(leads([{'id': 'a', 'text': 'ساعة بيعت في مزاد كبير.', 'set': 'room', 'params': {'asset': 'w1'}},
                               {'id': 'b', 'text': 'ما سرّها؟', 'set': 'room', 'params': {'asset': 'w2'}}]))


if __name__ == '__main__':
    unittest.main()
