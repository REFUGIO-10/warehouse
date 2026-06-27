"""Exact zero-congestion delivery ceiling for KNOWN seeds.

Congestion is ~0 (instrument.py: ~96% productive moves, ~0 collisions), so the
true per-seed max is each robot independently running its known shelf sequence on
shortest paths until the 300-tick clock runs out. We know the seed -> we know
every (robot, k) target exactly. trip_k = 2*dist(drop_r, access(shelf_k)) + 2
(PICKUP + DROP). Sum the trips a robot can finish in `ticks`. Sum over robots.

This is an upper bound no planner can beat. If the live SOTA per seed ~= this,
the contest is at the physical ceiling and only micro-margin remains.

  python tools/exact_ceiling.py SEED1 SEED2 ... [--layout-json L.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from pathlib import Path

_KIT = Path(__file__).resolve().parent.parent / "refugio-starter-kit"
if str(_KIT) not in sys.path:
    sys.path.insert(0, str(_KIT))

from warehouse.layout import (  # noqa: E402
    CellType, GRID_SIZE, grid_from_shelves, iter_base_cells, iter_shelf_cells,
)
from warehouse.state import drop_position_for_base  # noqa: E402
from warehouse.targets import target_for  # noqa: E402

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


def ceiling_for_seed(seed, shelves, passable, drops, access_of_shelf):
    # sorted shelf order == the engine's target indexing (build_layout sorts by y,x)
    shelf_list = sorted(shelves, key=lambda c: (c[1], c[0]))
    n_sh = len(shelf_list)
    total = 0
    per_robot = []
    for rid, drop in enumerate(drops):
        dist = _bfs(passable, drop)
        budget = TICKS
        k = 0
        done = 0
        while True:
            shelf = shelf_list[_idx(seed, rid, k, n_sh)]
            acc = access_of_shelf[shelf]
            d = min((dist.get(a, 10**6) for a in acc), default=10**6)
            trip = 2 * d + 2
            if budget - trip < 0:
                break
            budget -= trip
            done += 1
            k += 1
        total += done
        per_robot.append(done)
    return total, per_robot


def _idx(seed, rid, k, n):
    from warehouse.targets import target_index
    return target_index(seed, rid, k, n)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("seeds", nargs="+")
    p.add_argument("--layout-json", type=Path, default=None)
    args = p.parse_args()

    if args.layout_json:
        shelves = [tuple(s) for s in json.loads(args.layout_json.read_text())["shelves"]]
    else:
        shelves = list(iter_shelf_cells())
    grid = grid_from_shelves(shelves)
    passable = {(x, y) for y in range(GRID_SIZE) for x in range(GRID_SIZE)
                if grid[y][x] == CellType.EMPTY}
    drops = [drop_position_for_base(b.position) for b in iter_base_cells()]
    access_of_shelf = {}
    for (sx, sy) in shelves:
        access_of_shelf[(sx, sy)] = [(sx + dx, sy + dy) for dx, dy in _N4
                                     if (sx + dx, sy + dy) in passable]

    grand = 0
    print(f"{'seed':<34} {'ceiling':>8}")
    print("-" * 44)
    for s in args.seeds:
        tot, _ = ceiling_for_seed(s, shelves, passable, drops, access_of_shelf)
        grand += tot
        print(f"{s:<34} {tot:>8}")
    print("-" * 44)
    print(f"{'TOTAL (official-style sum)':<34} {grand:>8}")


if __name__ == "__main__":
    main()
