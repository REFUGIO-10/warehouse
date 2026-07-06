# layout_lab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an isolated `layout_lab/` that measures warehouse layouts with statistical signal (paired CRN bench + confidence intervals) and searches a parametrized layout space (grid + hill-climbing), emitting ranked results and a pasteable `create_layout()`.

**Architecture:** Pure-stdlib package under `layout_lab/`. `families.py` generates parametrized shelf lists; `harness.py` benches a layout against a fixed policy over shared seeds (Common Random Numbers) and computes a paired delta with a 95% CI verdict (SIGNAL/NOISE); `search.py` orchestrates a grid sweep + hill-climb and writes `results/`; `surrogate.py` is a stub for a future analytic prefilter. The lab only reads the engine (`refugio-starter-kit/`) and a policy file; it writes only inside `layout_lab/`.

**Tech Stack:** Python 3.12 stdlib only (`dataclasses`, `statistics`, `math`, `itertools`, `json`, `tempfile`, `argparse`, `unittest`). Engine reused via `warehouse.local_runner.run_local` and `warehouse.layout.validate_submitted_layout`.

## Global Constraints

- **Stdlib only** for the lab itself (no numpy/scipy) — only `python3` (3.12) is installed; no venv, no pytest.
- **Run everything from the repo root** (`/home/ruben/REFUGIO/warehouse`). The lab adds the kit and repo root to `sys.path` itself.
- **Touch nothing outside `layout_lab/`.** Do not edit `submissions/*`, `tools/*`, `refugio-starter-kit/*`, `AGENTS.md`, or `STRATEGY.md`.
- **Layout contract (validator rejects otherwise):** exactly **960** shelves, unique, integer coords in `1..50`, none on a base-entry cell, each shelf with ≥1 adjacent EMPTY cell (blocks ≤2 wide), all walkable cells connected, `create_layout()` deterministic. The lab keeps shelves within `2..49` to leave a perimeter aisle.
- **Engine call:** `run_local(Path(policy), layout_path=tmp, seeds=(s,), ticks=t, policy_budget_seconds=None)["score"]` returns deliveries for one seed.
- **CRN:** every candidate is measured on the *same* seed list; comparisons are paired over shared seeds only.
- **Calibration:** official ≈ `0.95 × (mean_per_seed × 3)`. Report both raw projection and calibrated.
- **Tests:** `unittest`, run as `python3 -m unittest layout_lab.tests.test_<name> -v` from repo root. Engine-free where possible (validation + math + monkeypatched orchestration); no slow full-sim in unit tests.
- **Git identity for commits:** `git -c user.name="rubensdg10" -c user.email="ruben229958@gmail.com" commit ...`. End commit messages with the Co-Authored-By trailer.

## File Structure

```
warehouse/
└── layout_lab/
    ├── __init__.py          # empty — marks package
    ├── families.py          # LayoutParams, generate(), canonical_baseline(), REGISTRY
    ├── harness.py           # Measurement, Delta, make_seeds(), bench(), compare()
    ├── search.py            # GRID, iter_grid(), grid_search(), hill_climb(), write_results(), CLI
    ├── surrogate.py         # prefilter() stub
    ├── README.md            # what it is, how to run, how to read results
    ├── results/
    │   └── .gitkeep         # results/*.json|md are regenerable outputs
    └── tests/
        ├── __init__.py      # empty — marks package
        ├── test_families.py
        ├── test_harness.py
        └── test_search.py
```

---

### Task 1: Package scaffold + `families.py`

**Files:**
- Create: `layout_lab/__init__.py`
- Create: `layout_lab/tests/__init__.py`
- Create: `layout_lab/families.py`
- Test: `layout_lab/tests/test_families.py`

**Interfaces:**
- Produces:
  - `LayoutParams(block_w:int=2, block_h:int=2, aisle:int=1, gradient:str="none", symmetric:bool=False)` — frozen dataclass.
  - `generate(params: LayoutParams) -> list[list[int]]` — shelves as `[x, y]`, sorted by `(y, x)`, exactly 960 for valid combos (fewer if the combo can't reach 960).
  - `canonical_baseline() -> list[list[int]]` — the proven 960-shelf canonical layout.
  - `REGISTRY: dict[str, Callable[[], list[list[int]]]]` — `{"baseline", "blocks_2x2", "blocks_2x3"}`.

- [ ] **Step 1: Write the failing test**

Create `layout_lab/__init__.py` and `layout_lab/tests/__init__.py` as **empty files** (needed for imports), then write `layout_lab/tests/test_families.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/ruben/REFUGIO/warehouse && python3 -m unittest layout_lab.tests.test_families -v`
Expected: FAIL / ERROR — `ModuleNotFoundError: No module named 'layout_lab.families'` (module not created yet).

- [ ] **Step 3: Write minimal implementation**

Create `layout_lab/families.py`:

```python
"""Parametrized layout families for the search lab.

A layout is a list of [x, y] shelf cells. The main family tiles blocks of
block_w x block_h shelves separated by aisles of width `aisle` in BOTH
directions, so every block edge gets a cross-aisle (the shape Equipo 03 used to
beat the ceiling). Demand is uniform over the 960 shelves, so we optimize
average accessibility, never specific cells.

generate() returns exactly 960 shelves for valid combos, sorted by (y, x).
Removing shelves only ever ADDS empty space, so any deterministic truncation
keeps the layout valid (every remaining shelf keeps its pickup neighbour and the
floor only gets more connected). Combos that can't reach 960 return fewer cells;
the harness's validator then marks them INVALID. Pure module: no engine import.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

LO, HI = 2, 49          # usable band: leaves a 2-cell perimeter aisle (no shelf on base-entry ring)
CENTER = 25.5           # geometric centre of the 1..50 interior
SHELF_COUNT = 960


@dataclass(frozen=True)
class LayoutParams:
    block_w: int = 2     # shelf columns per block (>2 traps inner cells -> invalid)
    block_h: int = 2     # shelf rows per block
    aisle: int = 1       # empty cells between blocks, both directions
    gradient: str = "none"   # "none" | "dense_edges" | "dense_center"
    symmetric: bool = False  # force 4-fold symmetry (central cross-aisle)


def _block_cells(block_w: int, block_h: int, aisle: int, lo: int, hi: int) -> list[tuple[int, int]]:
    cells: list[tuple[int, int]] = []
    px, py = block_w + aisle, block_h + aisle
    by = lo
    while by + block_h - 1 <= hi:
        bx = lo
        while bx + block_w - 1 <= hi:
            for dy in range(block_h):
                for dx in range(block_w):
                    cells.append((bx + dx, by + dy))
            bx += px
        by += py
    return cells


def _gradient_key(cell: tuple[int, int], gradient: str):
    x, y = cell
    d = abs(x - CENTER) + abs(y - CENTER)
    if gradient == "dense_edges":      # keep cells far from centre first
        return (-d, y, x)
    if gradient == "dense_center":     # keep cells near centre first
        return (d, y, x)
    return (y, x)                      # "none": top-left first


def generate(params: LayoutParams) -> list[list[int]]:
    if params.symmetric:
        # Generate one quadrant ([LO,24]^2), keep the best 240 by gradient, then
        # mirror across both axes -> exactly 960 with a central cross-aisle.
        quad = _block_cells(params.block_w, params.block_h, params.aisle, LO, 24)
        quad.sort(key=lambda c: _gradient_key(c, params.gradient))
        keep = quad[: SHELF_COUNT // 4]
        cells: set[tuple[int, int]] = set()
        for (x, y) in keep:
            cells.update({(x, y), (51 - x, y), (x, 51 - y), (51 - x, 51 - y)})
        ordered = sorted(cells, key=lambda c: (c[1], c[0]))
    else:
        full = _block_cells(params.block_w, params.block_h, params.aisle, LO, HI)
        full.sort(key=lambda c: _gradient_key(c, params.gradient))
        ordered = sorted(full[:SHELF_COUNT], key=lambda c: (c[1], c[0]))
    return [[x, y] for (x, y) in ordered]


def canonical_baseline() -> list[list[int]]:
    """The proven canonical layout: vertical 2-wide strips, 4 bands (exactly 960)."""
    shelves: list[list[int]] = []
    for x0 in range(3, 48, 4):
        for y0, y1 in ((3, 12), (15, 24), (27, 36), (39, 48)):
            for x in (x0, x0 + 1):
                for y in range(y0, y1 + 1):
                    shelves.append([x, y])
    return shelves


REGISTRY: dict[str, Callable[[], list[list[int]]]] = {
    "baseline": canonical_baseline,
    "blocks_2x2": lambda: generate(LayoutParams(2, 2, 1, "none", False)),
    "blocks_2x3": lambda: generate(LayoutParams(2, 3, 1, "none", False)),
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/ruben/REFUGIO/warehouse && python3 -m unittest layout_lab.tests.test_families -v`
Expected: PASS — all 8 tests OK. (If `test_blocks_2x2_valid_960` fails on count, the full tiling must exceed 960 so truncation hits exactly 960; `LO,HI=2,49` with pitch 3 yields 32×32=1024, so truncation to 960 is correct.)

- [ ] **Step 5: Commit**

```bash
cd /home/ruben/REFUGIO/warehouse
git add layout_lab/__init__.py layout_lab/tests/__init__.py layout_lab/families.py layout_lab/tests/test_families.py
git -c user.name="rubensdg10" -c user.email="ruben229958@gmail.com" commit -m "feat(layout_lab): parametrized layout families + generator

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: `harness.py` — reliable paired measurement

**Files:**
- Create: `layout_lab/harness.py`
- Test: `layout_lab/tests/test_harness.py`

**Interfaces:**
- Consumes: `families.generate`, `families.canonical_baseline` (Task 1); `run_local`, `validate_submitted_layout` (engine).
- Produces:
  - `Measurement(name:str, shelves:int, valid:bool, per_seed:dict[str,float], note:str)` with properties `mean_per_seed`, `projected` (×3), `calibrated` (×0.95).
  - `Delta(mean_diff:float, ci_low:float, ci_high:float)` with property `verdict` → `"SIGNAL+"` | `"SIGNAL-"` | `"NOISE"`.
  - `make_seeds(count:int) -> list[str]` → `["lab-0", ...]`.
  - `bench(name:str, shelves:list[list[int]], policy_path, seeds:list[str], ticks:int=300) -> Measurement`.
  - `compare(candidate: Measurement, baseline: Measurement) -> Delta` — paired over shared seeds.

- [ ] **Step 1: Write the failing test**

Create `layout_lab/tests/test_harness.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/ruben/REFUGIO/warehouse && python3 -m unittest layout_lab.tests.test_harness -v`
Expected: FAIL / ERROR — `No module named 'layout_lab.harness'`.

- [ ] **Step 3: Write minimal implementation**

Create `layout_lab/harness.py`:

```python
"""Reliable measurement for layout candidates: CRN bench + paired CI.

Fixes the failure recorded in STRATEGY.md (bench projected 910, official 866):
at few seeds the +-22 between layouts is noise. Here every candidate is measured
on the SAME seeds (Common Random Numbers) and compared to the baseline with a
PAIRED delta + 95% CI, so a real +N emerges even when absolute spread is large.
"""
from __future__ import annotations

import json
import math
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean, stdev

# Engine lives in refugio-starter-kit/.
_KIT = Path(__file__).resolve().parent.parent / "refugio-starter-kit"
if str(_KIT) not in sys.path:
    sys.path.insert(0, str(_KIT))

from warehouse.layout import LayoutValidationError, validate_submitted_layout  # noqa: E402
from warehouse.local_runner import run_local  # noqa: E402

DEFAULT_TICKS = 300
CALIBRATION = 0.95   # official ~= 0.95 x bench projection (904->882, 782->759)


@dataclass
class Measurement:
    name: str
    shelves: int
    valid: bool
    per_seed: dict[str, float] = field(default_factory=dict)
    note: str = "ok"

    @property
    def mean_per_seed(self) -> float:
        return mean(self.per_seed.values()) if self.per_seed else 0.0

    @property
    def projected(self) -> float:
        return self.mean_per_seed * 3

    @property
    def calibrated(self) -> float:
        return self.projected * CALIBRATION


@dataclass
class Delta:
    mean_diff: float     # paired mean of (candidate - baseline) per seed
    ci_low: float
    ci_high: float

    @property
    def verdict(self) -> str:
        if self.ci_low > 0:
            return "SIGNAL+"
        if self.ci_high < 0:
            return "SIGNAL-"
        return "NOISE"


def make_seeds(count: int) -> list[str]:
    return [f"lab-{i}" for i in range(count)]


def bench(name: str, shelves: list[list[int]], policy_path, seeds: list[str],
          ticks: int = DEFAULT_TICKS) -> Measurement:
    """Validate then score `shelves` under `policy_path` on each seed (CRN)."""
    try:
        validate_submitted_layout({"schema_version": 1, "shelves": shelves})
    except LayoutValidationError as exc:
        return Measurement(name, len(shelves), valid=False, note=f"INVALID: {exc}")

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump({"schema_version": 1, "shelves": shelves}, fh)
        layout_path = Path(fh.name)
    try:
        per_seed = {
            s: float(run_local(Path(policy_path), layout_path=layout_path,
                               seeds=(s,), ticks=ticks,
                               policy_budget_seconds=None)["score"])
            for s in seeds
        }
    finally:
        layout_path.unlink(missing_ok=True)
    return Measurement(name, len(shelves), valid=True, per_seed=per_seed)


def compare(candidate: Measurement, baseline: Measurement) -> Delta:
    """Paired delta over the seeds both measurements share (CRN)."""
    common = [s for s in candidate.per_seed if s in baseline.per_seed]
    diffs = [candidate.per_seed[s] - baseline.per_seed[s] for s in common]
    if not diffs:
        return Delta(0.0, 0.0, 0.0)
    m = mean(diffs)
    n = len(diffs)
    if n < 2:
        return Delta(m, m, m)
    half = 1.96 * stdev(diffs) / math.sqrt(n)
    return Delta(m, m - half, m + half)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/ruben/REFUGIO/warehouse && python3 -m unittest layout_lab.tests.test_harness -v`
Expected: PASS — 6 tests OK. (`test_bench_invalid_layout_marked_not_run` confirms validation happens before any `run_local`, so the dummy path is never used.)

- [ ] **Step 5: Commit**

```bash
cd /home/ruben/REFUGIO/warehouse
git add layout_lab/harness.py layout_lab/tests/test_harness.py
git -c user.name="rubensdg10" -c user.email="ruben229958@gmail.com" commit -m "feat(layout_lab): CRN bench harness with paired-CI signal verdict

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: `search.py` — grid sweep + hill-climb + results

**Files:**
- Create: `layout_lab/search.py`
- Test: `layout_lab/tests/test_search.py`

**Interfaces:**
- Consumes: `families.LayoutParams`, `families.generate`, `families.canonical_baseline` (Task 1); `harness.bench`, `harness.compare`, `harness.make_seeds`, `harness.Measurement`, `harness.Delta` (Task 2).
- Produces:
  - `GRID: dict[str, list]` — the parameter grid.
  - `param_name(p: LayoutParams) -> str` — stable human name, e.g. `"w2h2a1_none"` / `"w2h2a1_none_sym"`.
  - `iter_grid(grid=GRID) -> Iterator[LayoutParams]`.
  - `grid_search(policy_path, seeds, ticks, params_list) -> tuple[Measurement, list[Row]]` where `Row = (name:str, Measurement, Delta|None)`.
  - `hill_climb(policy_path, seeds, ticks, start: LayoutParams, baseline_m: Measurement) -> tuple[LayoutParams, Measurement]`.
  - `write_results(out_dir: Path, baseline_m, rows, best_params, best_m) -> None` — writes `rankings.json`, `best_layout.json`, `REPORT.md`.
  - CLI: `python3 layout_lab/search.py --count 20 --policy submissions/submission.py --ticks 300 --phase all [--only blocks_2x2,...]`.

- [ ] **Step 1: Write the failing test**

Create `layout_lab/tests/test_search.py` (monkeypatches `bench` so it never runs the sim — tests orchestration, not the engine):

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/ruben/REFUGIO/warehouse && python3 -m unittest layout_lab.tests.test_search -v`
Expected: FAIL / ERROR — `No module named 'layout_lab.search'`.

- [ ] **Step 3: Write minimal implementation**

Create `layout_lab/search.py`:

```python
"""Grid sweep + hill-climb over layout families, ranked by paired CRN bench.

Run from the repo root (warehouse/):
  python3 layout_lab/search.py                              # grid+hill, 20 seeds, submission.py policy
  python3 layout_lab/search.py --count 30 --phase grid
  python3 layout_lab/search.py --only blocks_2x2,blocks_2x3 --count 20
Writes layout_lab/results/{rankings.json,best_layout.json,REPORT.md}.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterator
from dataclasses import asdict, replace
from itertools import product
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent))  # repo root -> `import layout_lab...`

from layout_lab import families, harness  # noqa: E402

Row = tuple[str, "harness.Measurement", "harness.Delta | None"]

GRID: dict[str, list] = {
    "block_w": [2],
    "block_h": [2, 3, 4],
    "aisle": [1, 2],
    "gradient": ["none", "dense_edges", "dense_center"],
    "symmetric": [False, True],
}

DEFAULT_POLICY = _HERE.parent / "submissions" / "submission.py"
RESULTS_DIR = _HERE / "results"


def param_name(p: families.LayoutParams) -> str:
    base = f"w{p.block_w}h{p.block_h}a{p.aisle}_{p.gradient}"
    return base + "_sym" if p.symmetric else base


def iter_grid(grid: dict[str, list] = GRID) -> Iterator[families.LayoutParams]:
    keys = list(grid)
    for combo in product(*(grid[k] for k in keys)):
        yield families.LayoutParams(**dict(zip(keys, combo)))


def grid_search(policy_path, seeds, ticks, params_list) -> tuple["harness.Measurement", list[Row]]:
    baseline_m = harness.bench("baseline", families.canonical_baseline(), policy_path, seeds, ticks)
    rows: list[Row] = [("baseline", baseline_m, None)]
    for p in params_list:
        name = param_name(p)
        m = harness.bench(name, families.generate(p), policy_path, seeds, ticks)
        d = harness.compare(m, baseline_m) if m.valid else None
        rows.append((name, m, d))
    return baseline_m, rows


def _neighbors(p: families.LayoutParams) -> list[families.LayoutParams]:
    out: list[families.LayoutParams] = []
    for bh in (p.block_h - 1, p.block_h + 1):
        if 2 <= bh <= 4:
            out.append(replace(p, block_h=bh))
    for a in (p.aisle - 1, p.aisle + 1):
        if 1 <= a <= 2:
            out.append(replace(p, aisle=a))
    for g in ("none", "dense_edges", "dense_center"):
        if g != p.gradient:
            out.append(replace(p, gradient=g))
    out.append(replace(p, symmetric=not p.symmetric))
    return out


def hill_climb(policy_path, seeds, ticks, start, baseline_m) -> tuple[families.LayoutParams, "harness.Measurement"]:
    current = start
    current_m = harness.bench(param_name(current), families.generate(current), policy_path, seeds, ticks)
    improved = True
    while improved:
        improved = False
        for neighbor in _neighbors(current):
            m = harness.bench(param_name(neighbor), families.generate(neighbor), policy_path, seeds, ticks)
            if not m.valid:
                continue
            if harness.compare(m, current_m).verdict == "SIGNAL+":
                current, current_m = neighbor, m
                improved = True
                break  # greedy: take first significant improvement, re-expand
    return current, current_m


def _layout_snippet(shelves: list[list[int]]) -> str:
    return (
        "def create_layout():\n"
        f"    shelves = {shelves!r}\n"
        '    return {"schema_version": 1, "shelves": shelves}\n'
    )


def write_results(out_dir: Path, baseline_m, rows: list[Row], best_params, best_m) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    ranked = sorted(
        (r for r in rows if r[1].valid),
        key=lambda r: -r[1].mean_per_seed,
    )
    rankings = [
        {
            "name": name,
            "valid": m.valid,
            "shelves": m.shelves,
            "mean_per_seed": round(m.mean_per_seed, 2),
            "projected": round(m.projected, 1),
            "calibrated": round(m.calibrated, 1),
            "delta_vs_baseline": None if d is None else round(d.mean_diff, 2),
            "ci": None if d is None else [round(d.ci_low, 2), round(d.ci_high, 2)],
            "verdict": None if d is None else d.verdict,
        }
        for (name, m, d) in ranked
    ]
    (out_dir / "rankings.json").write_text(json.dumps(rankings, indent=2))

    best_shelves = families.generate(best_params)
    (out_dir / "best_layout.json").write_text(json.dumps({
        "params": asdict(best_params),
        "mean_per_seed": round(best_m.mean_per_seed, 2),
        "projected": round(best_m.projected, 1),
        "calibrated": round(best_m.calibrated, 1),
        "create_layout": _layout_snippet(best_shelves),
        "shelves": best_shelves,
    }, indent=2))

    lines = [
        "# layout_lab — results",
        "",
        f"Baseline (canonical): {baseline_m.mean_per_seed:.1f}/seed "
        f"-> proj {baseline_m.projected:.0f} (calibrated {baseline_m.calibrated:.0f}).",
        "",
        "| layout | /seed | proj | calib | delta | CI | verdict |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rankings:
        ci = "" if r["ci"] is None else f'[{r["ci"][0]}, {r["ci"][1]}]'
        delta = "" if r["delta_vs_baseline"] is None else f'{r["delta_vs_baseline"]:+}'
        lines.append(
            f'| {r["name"]} | {r["mean_per_seed"]} | {r["projected"]} | '
            f'{r["calibrated"]} | {delta} | {ci} | {r["verdict"] or ""} |'
        )
    lines += [
        "",
        f"**Best:** `{param_name(best_params)}` — proj {best_m.projected:.0f} "
        f"(calibrated {best_m.calibrated:.0f}). `create_layout()` in `best_layout.json`.",
        "",
        "> Regenerable output — do not edit by hand; re-run `layout_lab/search.py`.",
    ]
    (out_dir / "REPORT.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description="Search layouts, ranked by paired CRN bench.")
    ap.add_argument("--count", type=int, default=20, help="Number of CRN seeds lab-0..lab-{N-1}.")
    ap.add_argument("--policy", type=Path, default=DEFAULT_POLICY,
                    help="Submission whose act() measures layouts (its layout is overridden).")
    ap.add_argument("--ticks", type=int, default=300)
    ap.add_argument("--phase", choices=["grid", "hill", "all"], default="all")
    ap.add_argument("--only", default=None,
                    help="Comma-separated REGISTRY names instead of the full grid.")
    args = ap.parse_args()

    seeds = harness.make_seeds(args.count)
    policy = args.policy.resolve()
    print(f"policy={policy.name}  seeds={len(seeds)}  ticks={args.ticks}  phase={args.phase}\n")

    if args.only:
        names = [n.strip() for n in args.only.split(",")]
        # REGISTRY entries are concrete shelf-lists; wrap them as pseudo-params via baseline grid.
        params_list = [families.LayoutParams(2, 2, 1, "none", False)]  # placeholder; replaced below
        baseline_m = harness.bench("baseline", families.canonical_baseline(), policy, seeds, args.ticks)
        rows: list[Row] = [("baseline", baseline_m, None)]
        for n in names:
            m = harness.bench(n, families.REGISTRY[n](), policy, seeds, args.ticks)
            d = harness.compare(m, baseline_m) if m.valid else None
            rows.append((n, m, d))
    else:
        params_list = list(iter_grid())
        baseline_m, rows = grid_search(policy, seeds, args.ticks, params_list)

    for name, m, d in rows:
        if not m.valid:
            print(f"  {name:>22}  {m.note}")
        else:
            v = "" if d is None else f"  [{d.verdict} {d.mean_diff:+.1f}]"
            print(f"  {name:>22}  {m.mean_per_seed:6.1f}/seed -> proj {m.projected:.0f}{v}")

    valid_cand = [(n, m) for (n, m, _d) in rows if m.valid and n != "baseline"]
    best_name, best_m = max(valid_cand, key=lambda t: t[1].mean_per_seed) if valid_cand else ("baseline", baseline_m)

    best_params = families.LayoutParams(2, 2, 1, "none", False)
    if args.phase in ("hill", "all") and not args.only:
        # start hill-climb from the best grid candidate's params (re-derive by name match)
        for p in params_list:
            if param_name(p) == best_name:
                best_params = p
                break
        best_params, best_m = hill_climb(policy, seeds, args.ticks, best_params, baseline_m)
        print(f"\nhill-climb best: {param_name(best_params)} -> proj {best_m.projected:.0f}")

    write_results(RESULTS_DIR, baseline_m, rows, best_params, best_m)
    print(f"\nwrote {RESULTS_DIR}/rankings.json, best_layout.json, REPORT.md")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/ruben/REFUGIO/warehouse && python3 -m unittest layout_lab.tests.test_search -v`
Expected: PASS — 4 tests OK.

- [ ] **Step 5: Run the full unit suite (no engine)**

Run: `cd /home/ruben/REFUGIO/warehouse && python3 -m unittest layout_lab.tests.test_families layout_lab.tests.test_harness layout_lab.tests.test_search -v`
Expected: PASS — all tests green (none of these hit the simulator).

- [ ] **Step 6: Commit**

```bash
cd /home/ruben/REFUGIO/warehouse
git add layout_lab/search.py layout_lab/tests/test_search.py
git -c user.name="rubensdg10" -c user.email="ruben229958@gmail.com" commit -m "feat(layout_lab): grid+hill-climb search with ranked results

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: `surrogate.py` stub, README, results placeholder, smoke run

**Files:**
- Create: `layout_lab/surrogate.py`
- Create: `layout_lab/README.md`
- Create: `layout_lab/results/.gitkeep`

**Interfaces:**
- Produces: `surrogate.prefilter(candidates, top_k=None) -> list` — no-op passthrough until implemented.

- [ ] **Step 1: Create the surrogate stub**

Create `layout_lab/surrogate.py`:

```python
"""STUB: cheap analytic layout score to prefilter candidates before benching.

Idea (NOT yet implemented): score a layout WITHOUT running the simulator, e.g.
  sum over shelf pickup-cells of distance to nearest base   (travel proxy)
  + a congestion proxy from aisle width / local shelf density.
Rank thousands of candidates by it, then bench only the top-K. Build this only
once the grid sweep is the bottleneck (WHCA* ~2 s/seed x 20 seeds ~ 40 s per
candidate). Until then prefilter() is an identity passthrough so search.py can
call it unconditionally.
"""
from __future__ import annotations


def prefilter(candidates, top_k=None):
    """No-op until implemented: return candidates unchanged."""
    return list(candidates)
```

- [ ] **Step 2: Create the results placeholder**

Create `layout_lab/results/.gitkeep` as an **empty file** (keeps the dir in git; `rankings.json` / `best_layout.json` / `REPORT.md` are regenerable and will land here on the first real run).

- [ ] **Step 3: Write the README**

Create `layout_lab/README.md`:

```markdown
# `layout_lab/` — layout search (isolated)

Self-contained lab to find better shelf layouts **reliably**. It exists because
the bench lied once: `WHCA* + locked + blocks_2x2` projected 910 (6 seeds) but
scored **866** official (< 888). At few seeds the +-22 between layouts is noise.
This lab measures with **Common Random Numbers** (same seeds for every
candidate) and reports a **paired delta + 95% CI** with a SIGNAL/NOISE verdict,
then searches a parametrized layout space.

> Touches nothing outside this folder. Reads the engine (`refugio-starter-kit/`)
> and a policy file; writes only to `layout_lab/results/`. When it finds a
> winner it emits a pasteable `create_layout()` — a human decides if/when to
> wire it into `submissions/`.

## Run (from the repo root, `warehouse/`)

```bash
python3 layout_lab/search.py                       # full grid + hill-climb, 20 CRN seeds
python3 layout_lab/search.py --count 30 --phase grid
python3 layout_lab/search.py --only blocks_2x2,blocks_2x3 --count 20
python3 layout_lab/search.py --policy submissions/sota_equipo02.py   # measure vs another policy
```

Default policy is `submissions/submission.py` (its own layout is overridden, only
its `act()` is used). Pure stdlib — no install. ~40 s/candidate with a heavy
policy at 20 seeds, so the full 36-combo grid is ~20 min; use `--only` or a
smaller `--count` to iterate fast.

## Read the results (`layout_lab/results/`, regenerable — don't edit)

- `REPORT.md` — ranked table: `/seed`, projection (×3), **calibrated** (×0.95 ≈
  official), paired delta vs baseline, CI, and **verdict**. Trust SIGNAL+, ignore
  NOISE.
- `rankings.json` — same data as JSON.
- `best_layout.json` — winning params, scores, the 960 shelves, and a pasteable
  `create_layout()`.

## Files

| File | Responsibility |
|---|---|
| `families.py` | `LayoutParams` + `generate()` (block shape / aisle / gradient / symmetry); `REGISTRY` of named layouts. |
| `harness.py` | `bench()` (validate + score on CRN seeds), `compare()` (paired delta + CI), `Measurement`/`Delta`. |
| `search.py` | grid sweep + hill-climb; writes `results/`. CLI entry point. |
| `surrogate.py` | **stub**: future analytic prefilter (score without the sim). |

## Design space (what the search varies)

- `block_w` (≤2; wider traps inner cells = invalid), `block_h ∈ {2,3,4}`.
- `aisle ∈ {1,2}` between blocks, both directions (cross-aisle on every edge).
- `gradient ∈ {none, dense_edges, dense_center}` — the distance↔congestion knob.
- `symmetric` — 4-fold symmetry with a central cross-aisle.

Confirmed lever: thin blocks with a cross-aisle on every edge (Equipo 03, +38).
Long rows regress; over-density collapses. The lab quantifies which combo wins.
```

- [ ] **Step 4: Real smoke run (engine, fast settings)**

Run a tiny real search to prove the pipeline works end to end with the actual simulator (BFS policy is fast; small seeds/ticks/subset):

Run: `cd /home/ruben/REFUGIO/warehouse && python3 layout_lab/search.py --only blocks_2x2,blocks_2x3 --count 2 --ticks 60 --policy submissions/layout_dev.py`
Expected: prints a `baseline` line plus `blocks_2x2` / `blocks_2x3` lines with `/seed -> proj` numbers and a `[SIGNAL/NOISE ...]` tag, then `wrote .../rankings.json, best_layout.json, REPORT.md`. (Numbers will be low — 60 ticks — that's fine; this only proves the wiring.)

- [ ] **Step 5: Verify the results files and reset them**

Run: `cd /home/ruben/REFUGIO/warehouse && cat layout_lab/results/REPORT.md && python3 -c "import json;d=json.load(open('layout_lab/results/best_layout.json'));print('shelves:',len(d['shelves']))"`
Expected: a rendered table and `shelves: 960`.

Then discard the throwaway smoke outputs so only `.gitkeep` is committed (a real `--count 20` run produces the committed results):

Run: `cd /home/ruben/REFUGIO/warehouse && git checkout -- layout_lab/results/.gitkeep 2>/dev/null; rm -f layout_lab/results/rankings.json layout_lab/results/best_layout.json layout_lab/results/REPORT.md`

- [ ] **Step 6: Commit**

```bash
cd /home/ruben/REFUGIO/warehouse
git add layout_lab/surrogate.py layout_lab/README.md layout_lab/results/.gitkeep
git -c user.name="rubensdg10" -c user.email="ruben229958@gmail.com" commit -m "feat(layout_lab): surrogate stub, README, results placeholder

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Final verification (after all tasks)

- [ ] Full unit suite passes (engine-free):
  `cd /home/ruben/REFUGIO/warehouse && python3 -m unittest discover -s layout_lab/tests -t . -v`
- [ ] One real search at production settings produces SIGNAL/NOISE verdicts:
  `python3 layout_lab/search.py --count 20 --phase grid` (takes a while; confirms the harness distinguishes signal from noise on real seeds).
- [ ] `git status` shows changes only under `layout_lab/` (plus the spec/plan docs).
- [ ] Open a PR from `feature/layout-lab` so other agents can build on it.

## Self-Review (done while writing)

- **Spec coverage:** isolated folder ✔ (Task 1–4, constraint), reliable measurement w/ CRN+CI ✔ (Task 2), parametrized families incl. block shape/aisle/gradient/symmetry ✔ (Task 1), grid + hill-climb search ✔ (Task 3), surrogate stub ✔ (Task 4), results + pasteable `create_layout()` ✔ (Task 3 `write_results`/`best_layout.json`), measure on shippable policy default ✔ (Task 3 `DEFAULT_POLICY`), error handling (invalid → marked, not crash) ✔ (Task 2 `bench`).
- **Placeholder scan:** none — every step has full code/commands.
- **Type consistency:** `Measurement`/`Delta` fields and `bench`/`compare`/`generate`/`param_name` signatures match across Tasks 1–3; `REGISTRY` keys match the names asserted in tests.
- **Note:** `--only` uses `REGISTRY` (concrete shelf-lists) and skips hill-climb (no params to climb); the full grid path drives hill-climb. This is intentional and reflected in `main()`.
