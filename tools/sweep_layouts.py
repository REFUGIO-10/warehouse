"""Sweep candidate layouts against the BEST available policy, on the bench.

The current SOTA (Equipo 02, `submissions/sota_equipo02.py`) is a cooperative
A* MAPF planner scoring ~301/seed on the CANONICAL baseline layout — and it
left the layout untouched. So **layout is the unexploited lever on top of a
top-tier policy**. This runs each candidate layout WITH the SOTA policy's act()
(via the runner's layout override), so you measure a layout's real effect using
a strong planner instead of our weak BFS.

Add a candidate: write a function returning a list of [x, y] shelves and add it
to CANDIDATES. Invalid layouts are reported (with the reason) and skipped, never
crash the sweep — so experiment freely.

Run from the repo root (warehouse/):
  python tools/sweep_layouts.py
  python tools/sweep_layouts.py --count 5
  python tools/sweep_layouts.py --policy submissions/policy_dev.py --only baseline,wide_avenues
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from statistics import mean

# Engine lives in refugio-starter-kit/.
_KIT = Path(__file__).resolve().parent.parent / "refugio-starter-kit"
if str(_KIT) not in sys.path:
    sys.path.insert(0, str(_KIT))

from warehouse.layout import LayoutValidationError, validate_submitted_layout  # noqa: E402
from warehouse.local_runner import run_local  # noqa: E402

_REPO = Path(__file__).resolve().parent.parent
DEFAULT_POLICY = _REPO / "submissions" / "sota_equipo02.py"


# --- candidate layouts: each returns a list of [x, y] shelf cells ----------------
# Constraint learned the hard way: a shelf needs >=1 adjacent EMPTY cell, so solid
# blocks wider than 2 are INVALID (inner cells have no pickup access). Stick to
# strips <=2 wide separated by aisles.

def baseline() -> list[list[int]]:
    """Canonical: vertical 2-wide strips, 4 horizontal bands (pitch 4)."""
    shelves = []
    for x0 in range(3, 48, 4):
        for y0, y1 in ((3, 12), (15, 24), (27, 36), (39, 48)):
            for x in (x0, x0 + 1):
                for y in range(y0, y1 + 1):
                    shelves.append([x, y])
    return shelves


def wide_avenues() -> list[list[int]]:
    """Full-height vertical 2-wide strips with wider aisles (no horizontal bands)."""
    shelves = []
    for x0 in (4, 8, 13, 17, 22, 27, 32, 36, 41, 45):
        for x in (x0, x0 + 1):
            for y in range(2, 50):
                shelves.append([x, y])
    return shelves


def horizontal_bands() -> list[list[int]]:
    """Transpose of baseline: horizontal 2-wide strips, vertical aisles."""
    shelves = []
    for y0 in range(3, 48, 4):
        for x0, x1 in ((3, 12), (15, 24), (27, 36), (39, 48)):
            for y in (y0, y0 + 1):
                for x in range(x0, x1 + 1):
                    shelves.append([x, y])
    return shelves


CANDIDATES = {
    "baseline": baseline,
    "wide_avenues": wide_avenues,
    "horizontal_bands": horizontal_bands,
}


def _bench_layout(policy: Path, shelves: list[list[int]], seeds: list[str], ticks: int):
    """(mean_deliveries, note). Returns (None, reason) if the layout is invalid."""
    try:
        validate_submitted_layout({"schema_version": 1, "shelves": shelves})
    except LayoutValidationError as exc:
        return None, f"INVALID: {exc}"
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump({"schema_version": 1, "shelves": shelves}, fh)
        layout_path = Path(fh.name)
    try:
        scores = [
            run_local(policy, layout_path=layout_path, seeds=(s,), ticks=ticks,
                      policy_budget_seconds=None)["score"]
            for s in seeds
        ]
    finally:
        layout_path.unlink(missing_ok=True)
    return mean(scores), "ok"


def main() -> None:
    parser = argparse.ArgumentParser(description="Sweep layouts against a fixed policy.")
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY,
                        help="Submission whose act() is used (default: SOTA Equipo 02).")
    parser.add_argument("--count", type=int, default=3, help="Generated seeds bench-0..bench-{N-1}.")
    parser.add_argument("--ticks", type=int, default=300)
    parser.add_argument("--only", default=None, help="Comma-separated subset of candidate names.")
    args = parser.parse_args()

    seeds = [f"bench-{i}" for i in range(args.count)]
    names = [n.strip() for n in args.only.split(",")] if args.only else list(CANDIDATES)
    policy = args.policy.resolve()

    print(f"policy : {policy.name}   seeds: {len(seeds)}   ticks: {args.ticks}\n")
    results = []
    for name in names:
        shelves = CANDIDATES[name]()
        score, note = _bench_layout(policy, shelves, seeds, args.ticks)
        results.append((name, len(shelves), score, note))
        shown = f"{score:.1f}/seed -> proj {score * 3:.0f}" if score is not None else note
        print(f"  {name:>18}  shelves={len(shelves):>4}  {shown}")

    ranked = sorted((r for r in results if r[2] is not None), key=lambda r: -r[2])
    if ranked:
        print("\n--- ranked (best first) ---")
        base = next((r[2] for r in results if r[0] == "baseline" and r[2] is not None), None)
        for name, _n, score, _note in ranked:
            delta = f"  ({score - base:+.1f} vs baseline)" if base is not None else ""
            print(f"  {name:>18}  {score:.1f}/seed -> proj {score * 3:.0f}{delta}")


if __name__ == "__main__":
    main()
