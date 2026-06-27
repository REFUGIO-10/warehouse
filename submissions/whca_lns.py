"""WHCA* — windowed cooperative A* (centralized). Our own implementation.

Beats PIBT's 1-step reservation (~759) by planning WINDOW ticks ahead in
space-time with cell+edge reservations, so robots route around where
higher-priority robots WILL be, not just where they are. One centralized
planner runs on the first robot's call of each tick (module globals persist
across ticks/seeds) and serves the cached move to every robot.

Standard MAPF (Silver 2005, "Cooperative Pathfinding") — not anyone's IP.
Uses only stdlib + warehouse_api.

  python tools/check_submission.py submissions/whca.py
  python tools/benchmark.py submissions/whca.py --count 10
"""

from __future__ import annotations

import heapq
import os  # SWEEP-ONLY: remove before submit
from collections import deque

from warehouse_api import Action, CellType, Observation

GRID = 52
INF = 1 << 29
WINDOW = 24        # space-time reservation horizon (ticks)
NODE_CAP = 8000    # max A* expansions per robot before giving up
WAIT_CAP = 25      # cap on the starvation priority boost
FLOW_PENALTY = float(os.environ.get("FLOW", "0.2"))  # SWEEP-ONLY default
LNS_ITERS = int(os.environ.get("LNS", "3"))          # SWEEP-ONLY default

_DIRS: tuple[tuple[Action, int, int], ...] = (
    (Action.UP, 0, -1),
    (Action.DOWN, 0, 1),
    (Action.LEFT, -1, 0),
    (Action.RIGHT, 1, 0),
)


def _node(x: int, y: int) -> int:
    return y * GRID + x


def _flow_cost(x: int, y: int, nx: int, ny: int) -> float:
    """Soft one-way lanes: penalise moving against an aisle's preferred dir.

    Vertical aisle columns (x%3==2) alternate UP/DOWN by block; horizontal
    aisle rows (y%4==2) alternate LEFT/RIGHT. Tiny penalty (0.2) guides, never
    forces -> implicit traffic lanes, less head-on detour. Matched to the 2x3
    block period (px=3, py=4).
    """
    if x % 3 == 2:
        if (x // 3) % 2 == 0:
            if ny > y:
                return FLOW_PENALTY
        elif ny < y:
            return FLOW_PENALTY
    if y % 4 == 2:
        if (y // 4) % 2 == 0:
            if nx > x:
                return FLOW_PENALTY
        elif nx < x:
            return FLOW_PENALTY
    return 0.0


def create_layout() -> dict[str, object]:
    """Fine-grained 2x3 rack blocks, 1-cell aisles in BOTH directions.

    A cross-aisle at every block boundary -> robots cross sideways anywhere, so
    the cooperative planner avoids head-on gridlock. 2x3 (vs 2x2) packs denser
    -> shorter average trips, which matters because the bottleneck here is
    travel distance, not congestion. The tiling overfills 960, so surplus
    shelves are removed evenly (removing a shelf only frees space, keeping every
    rule valid). Deterministic and pure.
    """
    bw, bh, aw, ah, margin = 2, 3, 1, 1, 2
    lo, hi = 1 + margin, 50 - margin
    px, py = bw + aw, bh + ah
    cells: list[tuple[int, int]] = []
    x = lo
    while x <= hi:
        y = lo
        while y <= hi:
            for cx in range(x, min(x + bw, hi + 1)):
                for cy in range(y, min(y + bh, hi + 1)):
                    cells.append((cx, cy))
            y += py
        x += px
    n = len(cells)
    extra = n - 960
    if extra > 0:
        removed: set[int] = set()
        for k in range(extra):
            idx = (k * n) // extra + n // (2 * extra)
            while idx in removed:
                idx = (idx + 1) % n
            removed.add(idx)
        cells = [c for i, c in enumerate(cells) if i not in removed]
    return {"schema_version": 1, "shelves": [[cx, cy] for cx, cy in cells]}


def _base_entry(bx: int, by: int) -> tuple[int, int]:
    if bx == 0:
        return (1, by)
    if bx == GRID - 1:
        return (GRID - 2, by)
    if by == 0:
        return (bx, 1)
    return (bx, GRID - 2)


def _adjacent(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1


class _World:
    __slots__ = ("passable", "nbrs", "fields")

    def __init__(self, grid) -> None:
        passable = [False] * (GRID * GRID)
        for y in range(1, GRID - 1):
            row = grid[y]
            for x in range(1, GRID - 1):
                if row[x] == CellType.EMPTY:
                    passable[_node(x, y)] = True
        self.passable = passable
        nbrs: dict[int, tuple[tuple[Action, int], ...]] = {}
        for y in range(1, GRID - 1):
            for x in range(1, GRID - 1):
                i = _node(x, y)
                if not passable[i]:
                    continue
                lst = []
                for action, dx, dy in _DIRS:
                    nx, ny = x + dx, y + dy
                    j = _node(nx, ny)
                    if 0 <= nx < GRID and 0 <= ny < GRID and passable[j]:
                        lst.append((action, j))
                nbrs[i] = tuple(lst)
        self.nbrs = nbrs
        self.fields: dict[tuple, list[int]] = {}

    def _bfs(self, sources: list[int]) -> list[int]:
        dist = [INF] * (GRID * GRID)
        dq: deque[int] = deque()
        for s in sources:
            if dist[s] != 0:
                dist[s] = 0
                dq.append(s)
        nbrs = self.nbrs
        while dq:
            u = dq.popleft()
            du = dist[u] + 1
            for _action, v in nbrs[u]:
                if dist[v] > du:
                    dist[v] = du
                    dq.append(v)
        return dist

    def base_field(self, entry_node: int) -> list[int]:
        key = ("B", entry_node)
        field = self.fields.get(key)
        if field is None:
            field = self._bfs([entry_node])
            self.fields[key] = field
        return field

    def shelf_field(self, shelf: tuple[int, int]) -> list[int]:
        key = ("S", shelf)
        field = self.fields.get(key)
        if field is None:
            sx, sy = shelf
            sources = []
            for _action, dx, dy in _DIRS:
                nx, ny = sx + dx, sy + dy
                j = _node(nx, ny)
                if 0 <= nx < GRID and 0 <= ny < GRID and self.passable[j]:
                    sources.append(j)
            field = self._bfs(sources)
            self.fields[key] = field
        return field


class _Brain:
    __slots__ = (
        "world", "cur_tick", "pos", "entry", "target", "carrying",
        "wait_streak", "moves", "occupied", "need_greedy", "locked",
        "next_claimed", "planned_moves",
    )

    def __init__(self) -> None:
        self.world: _World | None = None
        self.cur_tick: int | None = None
        self.pos: dict[int, tuple[int, int]] = {}
        self.entry: dict[int, int] = {}
        self.target: dict[int, tuple[int, int] | None] = {}
        self.carrying: dict[int, bool] = {}
        self.wait_streak: dict[int, int] = {}
        self.moves: dict[int, Action] = {}
        self.occupied: frozenset[tuple[int, int]] = frozenset()
        self.need_greedy: frozenset[int] = frozenset()
        self.locked: frozenset[tuple[int, int]] = frozenset()
        self.next_claimed: set[tuple[int, int]] = set()
        self.planned_moves: dict[tuple[int, int], tuple[int, int]] = {}

    def reset_episode(self) -> None:
        self.cur_tick = None
        self.pos.clear()
        self.entry.clear()
        self.target.clear()
        self.carrying.clear()
        self.wait_streak.clear()
        self.moves.clear()
        self.occupied = frozenset()
        self.need_greedy = frozenset()
        self.locked = frozenset()
        self.next_claimed = set()
        self.planned_moves = {}


_BRAIN = _Brain()


def act(observation: Observation) -> Action:
    try:
        return _act(observation)
    except Exception:
        return Action.WAIT


def _act(obs: Observation) -> Action:
    brain = _BRAIN
    if brain.world is None:
        brain.world = _World(obs.grid)
    if brain.cur_tick is None or obs.tick != brain.cur_tick:
        if brain.cur_tick is None or obs.tick < brain.cur_tick:
            brain.reset_episode()
        brain.cur_tick = obs.tick
        try:
            _plan(brain, obs)
        except Exception:
            brain.moves = {}
            brain.next_claimed = set()
            brain.planned_moves = {}
    return _action_for(brain, obs)


def _plan(brain: _Brain, obs0: Observation) -> None:
    world = brain.world
    positions = obs0.all_robot_positions

    r0 = obs0.robot_id
    brain.pos[r0] = obs0.position
    brain.entry[r0] = _node(*_base_entry(*obs0.base_position))
    brain.target[r0] = obs0.target_item_position
    brain.carrying[r0] = obs0.carrying_item
    for rid, xy in positions.items():
        brain.pos[rid] = (xy[0], xy[1])

    rids = sorted(positions)
    brain.occupied = frozenset(brain.pos[rid] for rid in rids)
    brain.locked = frozenset(
        t for rid in rids
        if brain.carrying.get(rid) and (t := brain.target.get(rid)) is not None
    )

    stayers: list[int] = []
    movers: list[int] = []
    need_greedy: list[int] = []
    goal_field: dict[int, list[int]] = {}
    for rid in rids:
        node = _node(*brain.pos[rid])
        if brain.carrying.get(rid, False):
            entry = brain.entry.get(rid)
            if entry is None:
                stayers.append(rid)
                continue
            field = world.base_field(entry)
            if node == entry:
                stayers.append(rid)
                continue
        else:
            target = brain.target.get(rid)
            if target is None:
                stayers.append(rid)
                need_greedy.append(rid)
                continue
            field = world.shelf_field(target)
            if field[node] == 0:
                stayers.append(rid)
                continue
        if field[node] >= INF:
            stayers.append(rid)
            continue
        goal_field[rid] = field
        movers.append(rid)
    brain.need_greedy = frozenset(need_greedy)

    def priority(rid: int):
        node = _node(*brain.pos[rid])
        boost = min(brain.wait_streak.get(rid, 0), WAIT_CAP)
        return (0 if brain.carrying.get(rid, False) else 1, -boost,
                goal_field[rid][node], rid)

    starts = {rid: _node(*brain.pos[rid]) for rid in rids}

    def plan_with(order):
        cell_res: dict[tuple[int, int], int] = {}
        edge_res: dict[tuple[int, int, int], int] = {}
        for rid in stayers:
            for t in range(WINDOW + 1):
                cell_res[(t, starts[rid])] = rid
        desired = dict(starts)
        for rid in order:
            start = starts[rid]
            path = _astar(world, start, goal_field[rid], cell_res, edge_res)
            if path is None or len(path) < 2:
                desired[rid] = start
                for t in range(WINDOW + 1):
                    cell_res.setdefault((t, start), rid)
                continue
            desired[rid] = path[1]
            last = len(path) - 1
            for i in range(min(last, WINDOW) + 1):
                cell_res[(i, path[i])] = rid
            for i in range(min(last, WINDOW)):
                edge_res[(i, path[i], path[i + 1])] = rid
            for t in range(last + 1, WINDOW + 1):
                cell_res[(t, path[last])] = rid
        return desired

    def progress(desired):
        return sum(goal_field[rid][starts[rid]] - goal_field[rid][desired[rid]]
                   for rid in movers)

    # LNS-lite: from the priority order, repeatedly bump the worst-detour
    # movers (those making no goal-ward progress) to the front and replan,
    # keeping whichever order yields the most total goal-ward progress. Uses
    # the spare compute budget to recover detour overhead the single pass leaves.
    best_order = sorted(movers, key=priority)
    best_desired = plan_with(best_order)
    best_prog = progress(best_desired)
    for _ in range(LNS_ITERS):
        stuck = [rid for rid in best_order
                 if goal_field[rid][starts[rid]] - goal_field[rid][best_desired[rid]] <= 0]
        if not stuck:
            break
        stuck_set = set(stuck)
        new_order = stuck + [r for r in best_order if r not in stuck_set]
        if new_order == best_order:
            break
        cand = plan_with(new_order)
        cand_prog = progress(cand)
        if cand_prog > best_prog:
            best_prog, best_desired, best_order = cand_prog, cand, new_order
        else:
            break

    desired = best_desired
    order = stayers + best_order
    final = _resolve(brain, desired, order)

    moves: dict[int, Action] = {}
    claimed: set[tuple[int, int]] = set()
    planned: dict[tuple[int, int], tuple[int, int]] = {}
    for rid in rids:
        u = _node(*brain.pos[rid])
        v = final[rid]
        moves[rid] = _delta(u, v)
        brain.wait_streak[rid] = 0 if v != u else brain.wait_streak.get(rid, 0) + 1
        vc = (v % GRID, v // GRID)
        claimed.add(vc)
        if v != u:
            planned[(u % GRID, u // GRID)] = vc
    brain.moves = moves
    # Share the plan with just-delivered robots so their step never cancels a
    # coordinated mover (claimed = every robot's end cell this tick).
    brain.next_claimed = claimed
    brain.planned_moves = planned


def _astar(world, start, field, cell_res, edge_res):
    if field[start] >= INF:
        return None
    if field[start] == 0:
        return [start]
    nbrs = world.nbrs
    open_heap = [(field[start], 0, start, 0)]
    came: dict[tuple[int, int], tuple[int, int]] = {}
    gbest: dict[tuple[int, int], int] = {(start, 0): 0}
    expansions = 0
    goal_state = None
    while open_heap:
        _f, g, n, t = heapq.heappop(open_heap)
        if g > gbest.get((n, t), INF):
            continue
        if field[n] == 0:
            goal_state = (n, t)
            break
        expansions += 1
        if expansions > NODE_CAP:
            break
        nt = t + 1
        within = nt <= WINDOW
        nx0, ny0 = n % GRID, n // GRID
        for _action, m in nbrs[n]:
            if within and ((nt, m) in cell_res or (t, m, n) in edge_res):
                continue
            ng = g + 1.0 + _flow_cost(nx0, ny0, m % GRID, m // GRID)
            key = (m, nt)
            if ng < gbest.get(key, INF):
                gbest[key] = ng
                came[key] = (n, t)
                heapq.heappush(open_heap, (ng + field[m], ng, m, nt))
        if not (within and (nt, n) in cell_res):
            ng = g + 1.0
            key = (n, nt)
            if ng < gbest.get(key, INF):
                gbest[key] = ng
                came[key] = (n, t)
                heapq.heappush(open_heap, (ng + field[n], ng, n, nt))

    if goal_state is None:
        return None
    path = []
    state = goal_state
    while state in came:
        path.append(state[0])
        state = came[state]
    path.append(start)
    path.reverse()
    return path


def _resolve(brain, desired, order):
    cur = {rid: _node(*brain.pos[rid]) for rid in desired}
    final = dict(desired)
    by_cur = {cur[rid]: rid for rid in desired}

    for rid in order:
        u, v = cur[rid], final[rid]
        if v == u:
            continue
        other = by_cur.get(v)
        if other is not None and other != rid and final.get(other) == u:
            final[rid] = u
            final[other] = cur[other]

    changed = True
    guard = 0
    while changed and guard < 256:
        changed = False
        guard += 1
        occ: dict[int, int] = {}
        for rid in order:
            v = final[rid]
            if v in occ:
                if final[rid] != cur[rid]:
                    final[rid] = cur[rid]
                    changed = True
            else:
                occ[v] = rid
    return final


def _delta(u: int, v: int) -> Action:
    if u == v:
        return Action.WAIT
    dx = (v % GRID) - (u % GRID)
    if dx == 1:
        return Action.RIGHT
    if dx == -1:
        return Action.LEFT
    return Action.DOWN if (v // GRID) - (u // GRID) == 1 else Action.UP


def _action_for(brain: _Brain, obs: Observation) -> Action:
    rid = obs.robot_id
    pos = obs.position
    target = obs.target_item_position
    carrying = obs.carrying_item

    brain.pos[rid] = pos
    entry_xy = _base_entry(*obs.base_position)
    brain.entry[rid] = _node(*entry_xy)
    brain.target[rid] = target
    brain.carrying[rid] = carrying

    if carrying:
        if pos == entry_xy:
            brain.carrying[rid] = False
            brain.target[rid] = None
            return Action.DROP
    else:
        if _adjacent(pos, target) and target not in brain.locked:
            brain.carrying[rid] = True
            return Action.PICKUP

    move = brain.moves.get(rid)
    if move is None or (move == Action.WAIT and rid in brain.need_greedy):
        move = _coordinated_step(brain, obs)
    return move


def _coordinated_step(brain: _Brain, obs: Observation) -> Action:
    """Plan-aware step for a just-delivered robot (no target in the plan yet).

    Steps toward the goal field but refuses any cell another robot already
    claims this tick (`next_claimed`) and any edge swap against a planned mover
    (`planned_moves`), so it never cancels a coordinated move. Updates the
    shared claim sets so several such robots stay conflict-free together.
    """
    world = brain.world
    x, y = obs.position
    pos = (x, y)
    if obs.carrying_item:
        field = world.base_field(_node(*_base_entry(*obs.base_position)))
    else:
        target = obs.target_item_position
        if target is None:
            return Action.WAIT
        field = world.shelf_field(target)

    claimed = brain.next_claimed
    planned = brain.planned_moves
    claimed.discard(pos)  # no mover can enter a reserved stayer cell; safe to free
    best_action = Action.WAIT
    best_cell = pos
    best_key = (field[_node(x, y)], y, x)
    for action, dx, dy in _DIRS:
        nx, ny = x + dx, y + dy
        if not (0 <= nx < GRID and 0 <= ny < GRID):
            continue
        m = _node(nx, ny)
        if not world.passable[m]:
            continue
        cell = (nx, ny)
        if cell in claimed or planned.get(cell) == pos:
            continue
        key = (field[m], ny, nx)
        if key < best_key:
            best_key = key
            best_action = action
            best_cell = cell
    claimed.add(best_cell)
    if best_cell != pos:
        planned[pos] = best_cell
    return best_action
