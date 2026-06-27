"""Static mean-access-distance metric — predicts throughput without simulating.

Throughput is distance-bound (planner is ~96% productive, ~0 collisions), so the
layout that minimizes mean base->shelf-access distance wins. For a layout we BFS
from each of the 96 base drop cells and average, over shelves, the distance to the
nearest EMPTY neighbour of the shelf (its pickup cell). We also report a 1/(2d+2)
throughput proxy summed over robots.

  python tools/metric.py L1.json L2.json ...
  python tools/metric.py --ideal     # theoretical lower bound (960 most-central cells)
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from pathlib import Path
from statistics import mean

_KIT = Path(__file__).resolve().parent.parent / "refugio-starter-kit"
if str(_KIT) not in sys.path:
    sys.path.insert(0, str(_KIT))

from warehouse.layout import (  # noqa: E402
    CellType, GRID_SIZE, grid_from_shelves, iter_base_cells,
)
from warehouse.state import drop_position_for_base  # noqa: E402

TICKS = 300
_N4 = ((0, -1), (0, 1), (-1, 0), (1, 0))


def _bfs(passable, start):
    dist = {start: 0}
    dq = deque([start])
    while dq:
        cx, cy = dq.popleft()
        d = dist[(cx, cy)] + 1
        for dx, dy in _N4:
            n = (cx + dx, cy + dy)
            if n in passable and n not in dist:
                dist[n] = d
                dq.append(n)
    return dist


def analyze(layout: dict) -> tuple[float, float]:
    shelves = [(x, y) for (x, y) in (tuple(s) for s in layout["shelves"])]
    grid = grid_from_shelves(shelves)
    passable = {(x, y) for y in range(GRID_SIZE) for x in range(GRID_SIZE)
                if grid[y][x] == CellType.EMPTY}
    # access cell for each shelf = its empty neighbours
    access = []
    for sx, sy in shelves:
        nb = [(sx + dx, sy + dy) for dx, dy in _N4 if (sx + dx, sy + dy) in passable]
        if nb:
            access.append(nb)

    drops = [drop_position_for_base(b.position) for b in iter_base_cells()]
    per_robot_D = []
    throughput = 0.0
    for drop in drops:
        dist = _bfs(passable, drop)
        ds = [min((dist.get(n, 10**6) for n in nb)) for nb in access]
        D = mean(ds)
        per_robot_D.append(D)
        throughput += TICKS / (2 * D + 2)
    return mean(per_robot_D), throughput


def ideal_lower_bound() -> float:
    """960 cells closest to all bases (sum-dist), as a loose min-D bound."""
    bases = [drop_position_for_base(b.position) for b in iter_base_cells()]
    cells = []
    for y in range(1, GRID_SIZE - 1):
        for x in range(1, GRID_SIZE - 1):
            s = sum(abs(x - bx) + abs(y - by) for bx, by in bases)
            cells.append((s, (x, y)))
    cells.sort()
    chosen = [c for _, c in cells[:960]]
    return mean(min(abs(x - bx) + abs(y - by) for x, y in chosen) for bx, by in bases) \
        if False else _ideal_meanD(chosen, bases)


def _ideal_meanD(chosen, bases):
    return mean(mean(abs(x - bx) + abs(y - by) for x, y in chosen) for bx, by in bases)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("layouts", nargs="*", type=Path)
    p.add_argument("--ideal", action="store_true")
    args = p.parse_args()

    print(f"{'layout':<28} {'meanD':>7} {'throughput-proxy':>17}")
    print("-" * 56)
    if args.ideal:
        bases = [drop_position_for_base(b.position) for b in iter_base_cells()]
        cells = []
        for y in range(1, GRID_SIZE - 1):
            for x in range(1, GRID_SIZE - 1):
                s = sum(abs(x - bx) + abs(y - by) for bx, by in bases)
                cells.append((s, (x, y)))
        cells.sort()
        chosen = [c for _, c in cells[:960]]
        D = _ideal_meanD(chosen, bases)
        thr = sum(TICKS / (2 * mean(abs(x - bx) + abs(y - by) for x, y in chosen) + 2)
                  for bx, by in bases)
        print(f"{'IDEAL(960 central, Manhattan)':<28} {D:>7.2f} {thr:>17.0f}  (no aisles; loose bound)")

    for lp in args.layouts:
        layout = json.loads(lp.read_text())
        D, thr = analyze(layout)
        print(f"{lp.stem:<28} {D:>7.2f} {thr:>17.0f}")


if __name__ == "__main__":
    main()
