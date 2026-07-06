import json
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from layout_lab import families, harness, search


# Deterministic fake bench: score = 100 + bonus for 2x3 blocks + edges gradient.
def _fake_bench(name, shelves, policy_path, seeds, ticks=300):
    base = 100.0
    if "h3" in name:
        base += 8.0
    if name.endswith("edges") or "edges" in name:
        base += 4.0
    return harness.Measurement(name, len(shelves), valid=True,
                               per_seed={s: base for s in seeds})


class TestSearch(unittest.TestCase):
    def setUp(self):
        self._orig = harness.bench
        search.harness.bench = _fake_bench  # patch the name search.py calls

    def tearDown(self):
        search.harness.bench = self._orig

    def test_param_name_stable(self):
        p = families.LayoutParams(2, 3, 1, "dense_edges", True)
        self.assertEqual(search.param_name(p), "w2h3a1_dense_edges_sym")

    def test_iter_grid_yields_params(self):
        params = list(search.iter_grid())
        self.assertTrue(all(isinstance(p, families.LayoutParams) for p in params))
        self.assertGreater(len(params), 1)

    def test_grid_search_ranks_and_writes(self):
        seeds = harness.make_seeds(3)
        small = [
            families.LayoutParams(2, 2, 1, "none", False),
            families.LayoutParams(2, 3, 1, "none", False),
        ]
        baseline_m, rows = search.grid_search(Path("dummy.py"), seeds, 10, small)
        names = [r[0] for r in rows]
        self.assertIn("baseline", names)
        # the 2x3 candidate (h3 -> +8) must outrank the 2x2 candidate
        cand_rows = [r for r in rows if r[0] != "baseline"]
        ranked = sorted(cand_rows, key=lambda r: -r[1].mean_per_seed)
        self.assertIn("h3", ranked[0][0])

        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            best_name, best_m, _best_delta = ("baseline", baseline_m, None)
            search.write_results(out, baseline_m, rows,
                                 families.LayoutParams(2, 3, 1, "none", False),
                                 [r[1] for r in rows if "h3" in r[0]][0])
            self.assertTrue((out / "rankings.json").exists())
            self.assertTrue((out / "best_layout.json").exists())
            self.assertTrue((out / "REPORT.md").exists())
            best = json.loads((out / "best_layout.json").read_text())
            self.assertEqual(len(best["shelves"]), 960)

    def test_hill_climb_terminates_and_keeps_valid(self):
        seeds = harness.make_seeds(3)
        start = families.LayoutParams(2, 2, 1, "none", False)
        baseline_m = _fake_bench("baseline", families.canonical_baseline(), None, seeds)
        best_p, best_m = search.hill_climb(Path("dummy.py"), seeds, 10, start, baseline_m)
        self.assertTrue(best_m.valid)
        # climbing toward higher score should move block_h up (h3 bonus)
        self.assertGreaterEqual(best_p.block_h, start.block_h)


if __name__ == "__main__":
    unittest.main()
