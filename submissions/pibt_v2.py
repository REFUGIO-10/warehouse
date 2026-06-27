"""PIBT + layout probe — 5 shorter shelf bands (more cross-aisles).

Same PIBT policy as policy_pibt.py; only create_layout changes: 5 bands of 8
rows instead of 4 bands of 10, so robots hit a horizontal aisle more often
(shorter detours, less aisle congestion). Still exactly 960 shelves, base
entries open, fully connected.
"""

from __future__ import annotations

from collections import deque

from warehouse_api import Action, CellType, Observation, Position

_DIRS: tuple[tuple[Action, int, int], ...] = (
    (Action.RIGHT, 1, 0),
    (Action.LEFT, -1, 0),
    (Action.DOWN, 0, 1),
    (Action.UP, 0, -1),
)
_DELTAS: tuple[tuple[int, int], ...] = ((1, 0), (-1, 0), (0, 1), (0, -1))

_W = 0
_WALK: tuple[bool, ...] = ()
_READY = False
_SHELF_FIELD: dict[Position, list[int]] = {}
_BASE_FIELD: dict[Position, list[int]] = {}
_DROP: dict[Position, Position] = {}
_TICK = -1
_RESERVED: set[Position] = set()
_LEAVING: dict[Position, Position] = {}


def create_layout() -> dict[str, object]:
    # 5 bands of 8 rows: 12 col-pairs x 2 cols x 40 rows = 960. Aisles between
    # every band and column-pair; margins (x,y in {1,2,49,50}) kept clear so
    # base-entry cells stay open.
    shelves: list[list[int]] = []
    for x0 in range(3, 48, 4):
        for y0, y1 in ((2, 9), (12, 19), (22, 29), (32, 39), (42, 49)):
            for x in (x0, x0 + 1):
                for y in range(y0, y1 + 1):
                    shelves.append([x, y])
    return {"schema_version": 1, "shelves": shelves}


def _build(grid: tuple[tuple[CellType, ...], ...]) -> None:
    global _W, _WALK, _READY
    if _READY:
        return
    _W = len(grid)
    _WALK = tuple(
        grid[y][x] == CellType.EMPTY for y in range(_W) for x in range(_W)
    )
    _READY = True


def _bfs_field(sources: list[Position]) -> list[int]:
    w = _W
    dist = [-1] * (w * w)
    queue: deque[tuple[int, int]] = deque()
    for sx, sy in sources:
        if 0 <= sx < w and 0 <= sy < w and _WALK[sy * w + sx]:
            idx = sy * w + sx
            if dist[idx] == -1:
                dist[idx] = 0
                queue.append((sx, sy))
    while queue:
        x, y = queue.popleft()
        nd = dist[y * w + x] + 1
        for dx, dy in _DELTAS:
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < w:
                ni = ny * w + nx
                if _WALK[ni] and dist[ni] == -1:
                    dist[ni] = nd
                    queue.append((nx, ny))
    return dist


def _drop_cell(base: Position) -> Position:
    cached = _DROP.get(base)
    if cached is None:
        x, y = base
        if y == 0:
            cached = (x, 1)
        elif y == _W - 1:
            cached = (x, _W - 2)
        elif x == 0:
            cached = (1, y)
        else:
            cached = (_W - 2, y)
        _DROP[base] = cached
    return cached


def _base_field(drop: Position) -> list[int]:
    field = _BASE_FIELD.get(drop)
    if field is None:
        field = _bfs_field([drop])
        _BASE_FIELD[drop] = field
    return field


def _shelf_field(target: Position) -> list[int]:
    field = _SHELF_FIELD.get(target)
    if field is None:
        tx, ty = target
        sources = [(tx + dx, ty + dy) for dx, dy in _DELTAS]
        field = _bfs_field(sources)
        _SHELF_FIELD[target] = field
    return field


def act(observation: Observation) -> Action:
    global _TICK, _RESERVED, _LEAVING
    ob = observation
    _build(ob.grid)
    w = _W
    px, py = ob.position

    if not ob.carrying_item:
        tx, ty = ob.target_item_position
        if abs(px - tx) + abs(py - ty) == 1:
            return Action.PICKUP
        field = _shelf_field(ob.target_item_position)
    else:
        drop = _drop_cell(ob.base_position)
        if (px, py) == drop:
            return Action.DROP
        field = _base_field(drop)

    if ob.tick != _TICK:
        _TICK = ob.tick
        _RESERVED = set()
        _LEAVING = {}

    pos = (px, py)
    here = field[py * w + px]
    occupied = set(ob.all_robot_positions.values())
    occupied.discard(pos)
    rot = (ob.robot_id + ob.tick) % 4

    def claim(cell: Position, action: Action) -> Action:
        _RESERVED.add(cell)
        _LEAVING[pos] = cell
        return action

    def free(cell: Position) -> bool:
        if cell in _RESERVED:
            return False
        if cell in occupied and _LEAVING.get(cell, pos) == pos:
            return False
        return True

    ranked: list[tuple[int, int, int, Action, Position]] = []
    for i in range(4):
        action, dx, dy = _DIRS[(i + rot) % 4]
        nx, ny = px + dx, py + dy
        if not (0 <= nx < w and 0 <= ny < w and _WALK[ny * w + nx]):
            continue
        dn = field[ny * w + nx]
        if dn < 0:
            continue
        rank = 0 if dn < here else (1 if dn == here else 2)
        ranked.append((rank, dn, i, action, (nx, ny)))
    ranked.sort()
    for _rank, _dn, _i, action, cell in ranked:
        if free(cell):
            return claim(cell, action)

    for i in range(4):
        action, dx, dy = _DIRS[(i + rot) % 4]
        nx, ny = px + dx, py + dy
        if 0 <= nx < w and 0 <= ny < w and _WALK[ny * w + nx] and free((nx, ny)):
            return claim((nx, ny), action)

    _RESERVED.add(pos)
    return Action.WAIT
