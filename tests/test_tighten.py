"""tools/tighten_take.py: a take's long silences shortened, never its sounds (the owner: «نخليها اسرع شوي»)."""
from tests import _guard  # noqa: F401
import importlib.util, unittest
from pathlib import Path
spec = importlib.util.spec_from_file_location('tt', Path(__file__).resolve().parents[1] / 'tools/tighten_take.py')
tt = importlib.util.module_from_spec(spec); spec.loader.exec_module(tt)


class Tighten(unittest.TestCase):
    def test_only_long_inner_silences_are_cut(self):
        keep = tt.plan([(0, .3), (2, 3.2), (5, 5.3), (9, 10)], 10.0, .5)
        self.assertEqual(keep, [(0.0, 2.25), (2.95, 10.0)])          # the 1.2 s gap keeps 0.5 s; the ends and short gaps stay

    def test_times_follow_the_cut(self):
        keep = [(0.0, 2.25), (2.95, 10.0)]
        self.assertAlmostEqual(tt.remap(1.0, keep), 1.0)
        self.assertAlmostEqual(tt.remap(2.5, keep), 2.25)             # inside the cut: lands at the cut
        self.assertAlmostEqual(tt.remap(4.0, keep), 2.25 + 1.05)
