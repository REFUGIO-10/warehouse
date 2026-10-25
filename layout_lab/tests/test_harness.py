import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from layout_lab import harness


def _m(name, per_seed):
    return harness.Measurement(name=name, shelves=960, valid=True, per_seed=per_seed)


class TestHarness(unittest.TestCase):
    def test_make_seeds(self):
        self.assertEqual(harness.make_seeds(3), ["lab-0", "lab-1", "lab-2"])

    def test_measurement_projection_and_calibration(self):
        m = _m("x", {"lab-0": 100.0, "lab-1": 100.0})
        self.assertAlmostEqual(m.mean_per_seed, 100.0)
        self.assertAlmostEqual(m.projected, 300.0)
        self.assertAlmostEqual(m.calibrated, 285.0)

    def test_compare_signal_positive(self):
        base = _m("base", {"lab-0": 100.0, "lab-1": 102.0, "lab-2": 98.0, "lab-3": 100.0})
        cand = _m("cand", {"lab-0": 110.0, "lab-1": 112.0, "lab-2": 108.0, "lab-3": 110.0})
        d = harness.compare(cand, base)
        self.assertAlmostEqual(d.mean_diff, 10.0)
        self.assertGreater(d.ci_low, 0)
        self.assertEqual(d.verdict, "SIGNAL+")

    def test_compare_noise(self):
        base = _m("base", {"lab-0": 100.0, "lab-1": 100.0, "lab-2": 100.0, "lab-3": 100.0})
        cand = _m("cand", {"lab-0": 130.0, "lab-1": 70.0, "lab-2": 131.0, "lab-3": 69.0})
        d = harness.compare(cand, base)
        self.assertEqual(d.verdict, "NOISE")  # mean ~0, wide CI crosses 0

    def test_compare_uses_only_shared_seeds(self):
        base = _m("base", {"lab-0": 100.0, "lab-1": 100.0})
        cand = _m("cand", {"lab-0": 105.0, "lab-1": 105.0, "lab-9": 999.0})
        d = harness.compare(cand, base)
        self.assertAlmostEqual(d.mean_diff, 5.0)  # lab-9 ignored (not in baseline)

    def test_bench_invalid_layout_marked_not_run(self):
        # A 3x3 solid block traps inner cells -> invalid. bench must NOT run the
        # sim; a dummy policy path is fine because it returns before using it.
        from layout_lab import families
        shelves = families.generate(families.LayoutParams(3, 3, 1, "none", False))
        m = harness.bench("bad", shelves, Path("/nonexistent.py"), ["lab-0"])
        self.assertFalse(m.valid)
        self.assertTrue(m.note.startswith("INVALID"))
        self.assertEqual(m.per_seed, {})


if __name__ == "__main__":
    unittest.main()
