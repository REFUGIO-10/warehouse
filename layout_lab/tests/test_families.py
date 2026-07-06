import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_KIT = _ROOT / "refugio-starter-kit"
if str(_KIT) not in sys.path:
    sys.path.insert(0, str(_KIT))

from layout_lab import families
from warehouse.layout import LayoutValidationError, validate_submitted_layout


def _valid(shelves):
    validate_submitted_layout({"schema_version": 1, "shelves": shelves})


class TestFamilies(unittest.TestCase):
    def test_canonical_baseline_is_valid_960(self):
        shelves = families.canonical_baseline()
        self.assertEqual(len(shelves), 960)
        _valid(shelves)  # raises if invalid

    def test_blocks_2x2_valid_960(self):
        shelves = families.generate(families.LayoutParams(2, 2, 1, "none", False))
        self.assertEqual(len(shelves), 960)
        _valid(shelves)

    def test_blocks_2x3_valid_960(self):
        shelves = families.generate(families.LayoutParams(2, 3, 1, "none", False))
        self.assertEqual(len(shelves), 960)
        _valid(shelves)

    def test_symmetric_is_960_and_mirror_invariant(self):
        shelves = families.generate(families.LayoutParams(2, 2, 1, "none", True))
        self.assertEqual(len(shelves), 960)
        _valid(shelves)
        cells = {(x, y) for x, y in shelves}
        mirror = {(51 - x, 51 - y) for x, y in shelves}
        self.assertEqual(cells, mirror)  # 4-fold symmetric by construction

    def test_deterministic(self):
        p = families.LayoutParams(2, 3, 1, "dense_edges", False)
        self.assertEqual(families.generate(p), families.generate(p))

    def test_gradient_changes_the_set(self):
        p_edges = families.LayoutParams(2, 2, 1, "dense_edges", False)
        p_center = families.LayoutParams(2, 2, 1, "dense_center", False)
        self.assertNotEqual(families.generate(p_edges), families.generate(p_center))

    def test_three_wide_block_is_invalid(self):
        shelves = families.generate(families.LayoutParams(3, 3, 1, "none", False))
        with self.assertRaises(LayoutValidationError):
            _valid(shelves)  # inner column cells have no pickup access

    def test_registry_names(self):
        self.assertEqual(set(families.REGISTRY), {"baseline", "blocks_2x2", "blocks_2x3"})
        for name, fn in families.REGISTRY.items():
            self.assertEqual(len(fn()), 960, name)


if __name__ == "__main__":
    unittest.main()
