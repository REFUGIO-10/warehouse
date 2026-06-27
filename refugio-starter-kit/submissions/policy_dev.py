"""RAMA B / POLICY — iterate on act() here.

Only touch act() and its helpers. create_layout() is the proven baseline so you
measure the policy in isolation. This starts as the verbatim greedy from
submission.py (~132 deliveries/seed) — a CORRECT, non-regressing floor.

  python tools/check_submission.py submissions/policy_dev.py
  python tools/benchmark.py submissions/policy_dev.py --count 20

LEVERS: (1) precompute BFS distance fields AT IMPORT TIME (setup has its own ~180s
budget; act() must stay ~2 ms/call) and step to the lowest-distance neighbour so
robots route around shelf blocks instead of WAITing. (2) Coordination/reservations
help in theory but a naive per-tick reservation REGRESSED us ~5x (gridlock) — only
add it if the benchmark confirms it beats this floor.
"""

from __future__ import annotations

from collections import deque

from warehouse_api import Action, CellType, Observation, Position

DIRECTIONS: tuple[tuple[Action, Position], ...] = (
    (Action.UP, (0, -1)),
    (Action.RIGHT, (1, 0)),
    (Action.DOWN, (0, 1)),
    (Action.LEFT, (-1, 0)),
)

# id(grid) -> (passable: frozenset, neighbours: dict, grid). The grid content is
# constant for a whole eval, but the runner may hand us a fresh tuple each tick,
# so we fall back to content-equality before rebuilding.
# ponytail: tiny cache; cleared past 8 entries — only ever a handful of layouts.
_GRID_CACHE: dict[int, tuple[frozenset, dict, tuple]] = {}


def create_layout() -> dict[str, object]:
    shelves: list[list[int]] = []
    for x0 in range(3, 48, 4):
        for y0, y1 in ((3, 12), (15, 24), (27, 36), (39, 48)):
            for x in (x0, x0 + 1):
                for y in range(y0, y1 + 1):
                    shelves.append([x, y])
    return {"schema_version": 1, "shelves": shelves}


def act(observation: Observation) -> Action:
    if not observation.carrying_item and _adjacent(
        observation.position, observation.target_item_position
    ):
        return Action.PICKUP

    drop_cell = _drop_cell_for_base(observation.base_position)
    if observation.carrying_item and observation.position == drop_cell:
        return Action.DROP

    passable, neighbors = _grid_index(observation.grid)
    blocked = {
        pos
        for rid, pos in observation.all_robot_positions.items()
        if rid != observation.robot_id
    }

    if observation.carrying_item:
        goals = frozenset((drop_cell,))
    else:
        goals = _pickup_cells(observation.target_item_position, passable, blocked)
    if not goals:
        return Action.WAIT

    return _bfs_step(observation.position, goals, neighbors, blocked)


def _adjacent(a: Position, b: Position) -> bool:
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1


def _drop_cell_for_base(base: Position) -> Position:
    x, y = base
    if y == 0:
        return (x, 1)
    if y == 51:
        return (x, 50)
    if x == 0:
        return (1, y)
    return (50, y)


def _pickup_cells(
    target: Position, passable: frozenset, blocked: set
) -> frozenset:
    tx, ty = target
    return frozenset(
        cell
        for cell in ((tx + 1, ty), (tx - 1, ty), (tx, ty + 1), (tx, ty - 1))
        if cell in passable and cell not in blocked
    )


def _grid_index(grid: tuple[tuple[CellType, ...], ...]) -> tuple[frozenset, dict]:
    key = id(grid)
    hit = _GRID_CACHE.get(key)
    if hit is None:
        hit = next((c for c in _GRID_CACHE.values() if c[2] == grid), None)
        if hit is None:
            passable = frozenset(
                (x, y)
                for y, row in enumerate(grid)
                for x, cell in enumerate(row)
                if cell == CellType.EMPTY
            )
            neighbors = {
                (x, y): tuple(
                    (action, (x + dx, y + dy))
                    for action, (dx, dy) in DIRECTIONS
                    if (x + dx, y + dy) in passable
                )
                for (x, y) in passable
            }
            hit = (passable, neighbors, grid)
        if len(_GRID_CACHE) > 8:
            _GRID_CACHE.clear()
        _GRID_CACHE[key] = hit
    return hit[0], hit[1]


def _bfs_step(
    start: Position, goals: frozenset, neighbors: dict, blocked: set
) -> Action:
    """First action of a shortest path to the nearest goal; WAIT if boxed in.

    Neighbours are in fixed DIRECTIONS order, so shortest-path ties break
    deterministically by direction — required: the evaluator re-runs the policy.
    """
    if start in goals:
        return Action.WAIT

    visited = {start}
    queue: deque[tuple[Position, Action]] = deque()
    for action, nxt in neighbors.get(start, ()):
        if nxt in blocked:
            continue
        if nxt in goals:
            return action
        visited.add(nxt)
        queue.append((nxt, action))

    while queue:
        pos, first = queue.popleft()
        for action, nxt in neighbors.get(pos, ()):
            if nxt in visited or nxt in blocked:
                continue
            if nxt in goals:
                return first
            visited.add(nxt)
            queue.append((nxt, first))
    return Action.WAIT
