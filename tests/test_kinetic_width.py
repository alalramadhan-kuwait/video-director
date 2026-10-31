from tests import _guard  # noqa: F401
import unittest

from director.studio import art


class TestKineticLineWidth(unittest.TestCase):
    def test_line_width_defaults_and_caps(self):
        p = {'lines': [{'text': 'a'}, {'text': 'b', 'w': 360, 'paper': True}, {'text': 'c', 'w': 900}]}
        els = [e for e in art.b_kinetic_type(p, 'tk-graphite', 6)['elements'] if e['type'] == 'text']
        self.assertEqual([e['w'] for e in els], [640, 360, 640])


if __name__ == '__main__':
    unittest.main()
