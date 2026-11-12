"""The style gate as a tool (the owner, 10 Nov 2026: «The style stage was skipped… built «فيديو v1» without showing me
the style card»): tools/studio_gate.py refuses a build unless the film's record shows his pick."""
from tests import _guard  # noqa: F401
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from director import style_gate
from tools import studio_gate

PAGE = {'style_pick': {'by': 'owner', 'at': '2026-11-10T15:00:00Z', 'choice': 'ink', 'name': 'حبر', 'via': 'card'}}
CHAT = {'flow': {'stage': 'done', 'choice': 'ink'}, 'style_pick_chat': {'at': '2026-11-10T15:00:00Z', 'words': 'ابي الحبر'}}


def run(doc, by_stdin=False):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        if by_stdin:
            rc = studio_gate.main(['-'], stdin=io.StringIO(doc if isinstance(doc, str) else json.dumps(doc, ensure_ascii=False)))
        else:
            f = Path(tempfile.mkdtemp()) / 'film.json'
            f.write_text(doc if isinstance(doc, str) else json.dumps(doc, ensure_ascii=False), encoding='utf-8')
            rc = studio_gate.main([str(f)])
    return rc, out.getvalue()


class Gate(unittest.TestCase):
    def test_his_tap_on_the_page_opens_the_build(self):
        self.assertEqual(style_gate.problems(PAGE), [])
        rc, said = run(PAGE)
        self.assertEqual(rc, 0); self.assertIn('حبر', said)
        self.assertEqual(run({'id': 'f1', 'data': PAGE})[0], 0)                      # the row passed whole

    def test_his_pick_in_chat_opens_it_only_with_all_three(self):
        self.assertEqual(run(CHAT, by_stdin=True)[0], 0)
        for broken in ({**CHAT, 'flow': {'stage': 'done', 'choice': ''}},             # no choice
                       {**CHAT, 'flow': {'stage': 'direction', 'choice': 'ink'}},     # the card is still open
                       {'flow': CHAT['flow']},                                        # nothing says he picked it
                       {**CHAT, 'style_pick_chat': {'at': '2026-11-10T15:00:00Z', 'words': ' '}},
                       {**CHAT, 'style_pick_chat': {'words': 'ابي الحبر'}}):
            rc, said = run(broken)
            self.assertEqual(rc, 1, broken); self.assertIn('no style pick from the owner', said)

    def test_a_pick_that_is_not_his_is_refused_with_the_reason(self):
        for film, why in (({}, 'no `style_pick` from the page'),
                          ({'style_pick': {'by': 'claude', 'choice': 'ink'}}, "'claude'"),
                          ({'style_pick': {'by': 'owner', 'choice': ''}}, '`style_pick.choice` is empty'),
                          ({'video': 'film/x.mp4', 'step': 7, 'flow': {'stage': 'done', 'choice': 'ink'}}, 'style_pick_chat')):
            rc, said = run(film)
            self.assertEqual(rc, 1, film); self.assertIn(why, said); self.assertIn('show him the style card', said)

    def test_a_line_in_changes_is_not_a_pick(self):
        film = {'flow': {'stage': 'done', 'choice': 'ink'}, 'changes': ['اخترت الحبر'],
                'versions': [{'changes': ['اخترت الحبر']}]}
        self.assertEqual(run(film)[0], 1)

    def test_a_record_that_cannot_be_read_builds_nothing(self):
        self.assertEqual(run('not json')[0], 2)
        self.assertEqual(run('[]')[0], 1)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(studio_gate.main(['/no/such/film.json']), 2)


if __name__ == '__main__':
    unittest.main()
