"""A film flows (rule 3b; the owner on the rubies film: «not connected… no transition in the wording, the sound, the ideas»):
acts, lines that hand on, one voice take per act, dissolves inside an act and a push only into a new one."""
from tests import _guard  # noqa: F401
import unittest

from director import quickfilm
from tools import record_flow as rf

PIC = {'elements': [{'type': 'photo', 'asset': 'a', 'w': 400, 'aspect': 1, 'x': 360, 'y': 600}]}
WORDS = {'elements': [{'type': 'text', 'text': 'كلمة', 'size': 60, 'x': 360, 'y': 600, 'w': 400}]}


def cut(ln, prev, sc, flow=True, last=None):
    return quickfilm.cut_for(ln, prev, sc, None, 'archive_photo', last, flow=flow)


class Cuts(unittest.TestCase):
    def test_inside_an_act_the_scenes_dissolve_and_never_whip(self):
        self.assertEqual(cut({'id': 'b'}, PIC, PIC), 'match')
        self.assertEqual(cut({'id': 'b'}, WORDS, PIC), 'fade')
        self.assertEqual(cut({'id': 'b'}, WORDS, WORDS, last='fade'), 'fade')

    def test_a_new_act_is_pushed_into(self):
        self.assertEqual(cut({'id': 'b', 'act': True}, WORDS, PIC), 'through')

    def test_the_line_still_decides_and_old_films_keep_their_cuts(self):
        self.assertEqual(cut({'id': 'b', 'cut': 'whip'}, WORDS, PIC), 'whip')
        self.assertIn(cut({'id': 'b'}, WORDS, WORDS, flow=False, last='through'), ('whip', 'through'))


class Wording(unittest.TestCase):
    def lines(self, second, acts=True):
        return [{'id': 'l1', 'text': 'كانت الثقوب من نحاس', 'template': 'kinetic_type', 'params': {}, 'no_photo': 't', 'act': acts},
                {'id': 'l2', 'text': second, 'template': 'kinetic_type', 'params': {}, 'no_photo': 't'}]

    def faults(self, second, acts=True):
        return [m for m in quickfilm.story_check({'brand': 'timekeeper', 'lines': self.lines(second, acts)}) if m.startswith('l2')]

    def test_a_film_made_before_acts_keeps_its_dates(self):
        self.assertEqual([m for m in self.faults('وفي 1902 صنع فيرنوي الياقوت', acts=False) if 'bridge' in m], [])

    def test_a_date_is_not_a_bridge(self):
        self.assertTrue(any('a date is not a bridge' in m for m in self.faults('وفي 1902 صنع فيرنوي الياقوت')))

    def test_a_line_that_carries_the_years_is(self):
        self.assertEqual([m for m in self.faults('وبقي الياقوت غاليًا قرنين… حتى صنعه فيرنوي في 1902') if 'bridge' in m or 'leading' in m], [])
        self.assertEqual([m for m in self.faults('نرجع لسؤالنا… 17 تكفي') if 'leading' in m], [])


class OneTakePerAct(unittest.TestCase):
    def test_acts_open_at_each_marked_line(self):
        ls = [{'id': 'a'}, {'id': 'b'}, {'id': 'c', 'act': True}, {'id': 'd'}]
        self.assertEqual([[x['id'] for x in g] for g in rf.acts(ls)], [['a', 'b'], ['c', 'd']])

    def test_the_act_is_one_paragraph_with_each_line_placed_in_it(self):
        text, spans = rf.paragraph(['سؤال؟', 'جواب', 'وبعد…'])
        self.assertEqual(text, 'سؤال؟ جواب. وبعد…')
        self.assertEqual([text[a:b] for a, b in spans], ['سؤال؟', 'جواب.', 'وبعد…'])

    def test_lines_are_cut_in_the_middle_of_the_silence_between_them(self):
        spans = [(0, 2), (3, 5)]
        starts = [0.0, 0.2, 0.0, 1.4, 1.6]
        ends = [0.2, 0.6, 0.6, 1.6, 1.9]
        self.assertEqual(rf.cuts(spans, starts, ends, 2.2), [(0.0, 1.0), (1.0, 2.2)])


if __name__ == '__main__':
    unittest.main()


class Emotion(unittest.TestCase):
    """The owner chose Faisal on eleven_v3 with emotion («اعتمد ٢»): a line's `emotion:` is an audio tag the voice
    performs on v3, never on the older model, and the screen text never carries it."""
    def test_the_tag_goes_in_front_on_v3_only(self):
        ln = {'id': 'l0', 'text': 'بنت تسبح بالبحر…', 'emotion': 'calm, curious'}
        self.assertEqual(rf.tagged(ln, 'بنت تسبح بالبحر…', rf.V3), '[calm, curious] بنت تسبح بالبحر…')
        self.assertEqual(rf.tagged(ln, 'بنت تسبح بالبحر…', 'eleven_multilingual_v2'), 'بنت تسبح بالبحر…')
        self.assertEqual(rf.tagged({'id': 'l1', 'text': 'x'}, 'x', rf.V3), 'x')

    def test_v3_settings_are_its_own(self):
        self.assertNotIn('style', rf.SETTINGS_V3)
        self.assertLess(rf.SETTINGS_V3['speed'], 1.0)


class Streamed(unittest.TestCase):
    def test_pieces_join_into_one_answer(self):
        import base64, json
        a = {'audio_base64': base64.b64encode(b'AB').decode(), 'alignment': {'characters': ['x'], 'character_start_times_seconds': [0.0], 'character_end_times_seconds': [.1]}}
        b = {'audio_base64': base64.b64encode(b'CD').decode(), 'alignment': {'characters': ['y'], 'character_start_times_seconds': [.1], 'character_end_times_seconds': [.2]}}
        d = rf.joined(json.dumps(a) + '\n' + json.dumps(b) + '\n')
        self.assertEqual(base64.b64decode(d['audio_base64']), b'ABCD')
        self.assertEqual(d['alignment']['characters'], ['x', 'y'])
        with self.assertRaises(RuntimeError):
            rf.joined('{"detail": "quota"}')
