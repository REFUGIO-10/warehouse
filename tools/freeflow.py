"""Free-flow (zero-congestion) delivery ceiling per layout.

For each candidate shelf set we compute:
  - validity sanity (960 shelves, every shelf has an empty cardinal neighbor,
    floor connected)
  - average round-trip distance over uniform (base, shelf) demand
  - free-flow deliveries/seed: 96 robots, each run INDEPENDENTLY (no collisions)
    over 300 ticks against the real sha256 target stream, greedy round trips.

That free-flow number is the hard upper bound a layout can ever reach. Comparing
it to the observed ~296/seed (=888/3) tells us how much is left on the table by
DISTANCE (layout) vs CONGESTION (policy).
"""
from __future__ import annotations
import hashlib
from collections import deque

GRID = 52
LO, HI = 1, 50
N_ROBOTS = 96
TICKS = 300
INF = 1 << 29


def base_entries() -> list[tuple[int, int]]:
    e = []
    for x in range(3, 50, 2):
        e.append((x, 1))        # top
    for x in range(2, 49, 2):
        e.append((x, 50))       # bottom
    for y in range(2, 49, 2):
        e.append((1, y))        # left
    for y in range(3, 50, 2):
        e.append((50, y))       # right
    return e                    # 96, in robot_id order


def _node(x, y):
    return y * GRID + x


def build_passable(shelves: set[tuple[int, int]]):
    passable = [False] * (GRID * GRID)
    for y in range(LO, HI + 1):
        for x in range(LO, HI + 1):
            if (x, y) not in shelves:
                passable[_node(x, y)] = True
    return passable


def bfs_from(sources, passable):
    dist = [INF] * (GRID * GRID)
    dq = deque()
    for s in sources:
        if passable[s] and dist[s] != 0:
            dist[s] = 0
            dq.append(s)
    while dq:
        u = dq.popleft()
        ux, uy = u % GRID, u // GRID
        du = dist[u] + 1
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            nx, ny = ux + dx, uy + dy
            if LO <= nx <= HI and LO <= ny <= HI:
                v = _node(nx, ny)
                if passable[v] and dist[v] > du:
                    dist[v] = du
                    dq.append(v)
    return dist


def shelf_access_dist(shelf, entry_field, passable):
    """min dist from entry to a cell cardinally adjacent & walkable to shelf."""
    sx, sy = shelf
    best = INF
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        nx, ny = sx + dx, sy + dy
        if LO <= nx <= HI and LO <= ny <= HI:
            n = _node(nx, ny)
            if passable[n] and entry_field[n] < best:
                best = entry_field[n]
    return best


def target_index(seed, rid, k, n):
    key = f"{seed}|{rid}|{k}".encode()
    return int.from_bytes(hashlib.sha256(key).digest()[:8], "big") % n


def analyze(name, shelves, seeds=("round-0", "round-1", "round-2")):
    shelves = [tuple(s) for s in shelves]
    n = len(shelves)
    sset = set(shelves)
    passable = build_passable(sset)

    # validity
    n_walk = sum(passable)
    # connectivity
    start = next(i for i in range(GRID * GRID) if passable[i])
    reach = bfs_from([start], passable)
    connected = sum(1 for i in range(GRID * GRID) if passable[i] and reach[i] < INF)
    conn_ok = connected == n_walk
    # every shelf has cardinal empty neighbor
    bad = 0
    for (sx, sy) in shelves:
        ok = False
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            nx, ny = sx + dx, sy + dy
            if LO <= nx <= HI and LO <= ny <= HI and (nx, ny) not in sset:
                ok = True
                break
        if not ok:
            bad += 1

    entries = base_entries()
    fields = [bfs_from([_node(*e)], passable) for e in entries]

    # average round-trip over uniform (base, shelf)
    sorted_shelves = sorted(shelves, key=lambda c: (c[1], c[0]))
    total_one_way = 0
    cnt = 0
    per_shelf_access = []
    for f in fields:
        for s in sorted_shelves:
            d = shelf_access_dist(s, f, passable)
            if d < INF:
                total_one_way += d
                cnt += 1
    avg_one_way = total_one_way / cnt
    avg_round = 2 * avg_one_way + 2  # +2 for PICKUP & DROP ticks

    # free-flow deliveries/seed: independent robots, real target stream
    ff_per_seed = []
    for seed in seeds:
        total_deliv = 0
        for rid in range(N_ROBOTS):
            f = fields[rid]
            t = 0
            k = 0
            while True:
                s = sorted_shelves[target_index(seed, rid, k, n)]
                d = shelf_access_dist(s, f, passable)
                cycle = 2 * d + 2
                if t + cycle > TICKS:
                    break
                t += cycle
                total_deliv += 1
                k += 1
        ff_per_seed.append(total_deliv)
    ff_avg = sum(ff_per_seed) / len(ff_per_seed)

    print(f"\n=== {name} ===")
    print(f"  shelves={n}  walkable={n_walk}  connected={'OK' if conn_ok else 'BROKEN'}  "
          f"no-access shelves={bad}")
    print(f"  avg one-way dist = {avg_one_way:6.2f}   avg round-trip = {avg_round:6.2f} ticks")
    print(f"  FREE-FLOW deliveries/seed = {ff_avg:7.1f}   (x3 = {ff_avg*3:7.0f})")
    return ff_avg, avg_round


# ---- candidate layouts ----

def layout_2x3_blocks():
    bw, bh, aw, ah, margin = 2, 3, 1, 1, 2
    lo, hi = 1 + margin, 50 - margin
    px, py = bw + aw, bh + ah
    cells = []
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
        removed = set()
        for kk in range(extra):
            idx = (kk * n) // extra + n // (2 * extra)
            while idx in removed:
                idx = (idx + 1) % n
            removed.add(idx)
        cells = [c for i, c in enumerate(cells) if i not in removed]
    return cells


def base_entry_set():
    return set(base_entries())


def layout_central_cluster():
    """960 most-central cells, packed as 2-wide vertical strips + 1 aisle,
    confined to a central square so a wide empty ring road surrounds them.
    Distance-minimizing: shelves concentrate near centroid, far from corners."""
    # pick a central square big enough; 2/3 packing => need ~1440 area => 38x38.
    entries = base_entry_set()
    # 2-wide vertical strips with 1-cell aisle, but only keep central-most cells.
    candidates = []
    for x in range(LO, HI + 1):
        if x % 3 == 0:   # aisle columns at x divisible by 3 -> strips are 2 wide
            continue
        for y in range(LO, HI + 1):
            if (x, y) in entries:
                continue
            candidates.append((x, y))
    # add horizontal cross-aisles every 4 rows to keep blocks <= 3 tall & cross flow
    candidates = [(x, y) for (x, y) in candidates if y % 4 != 0]
    # rank by centrality (distance to center 25.5,25.5), keep 960 closest
    candidates.sort(key=lambda c: (c[0] - 25.5) ** 2 + (c[1] - 25.5) ** 2)
    return candidates[:960]


def layout_diamond():
    """Distance-min: keep the 960 cells with smallest total-distance-to-all-bases,
    but enforce 2-wide strip + aisle validity via column/row skips."""
    entries = base_entry_set()
    passable_all = [True] * (GRID * GRID)
    cells = []
    for x in range(LO, HI + 1):
        if x % 3 == 0:
            continue
        for y in range(LO, HI + 1):
            if y % 5 == 0:
                continue
            if (x, y) in entries:
                continue
            cells.append((x, y))
    # Phi(s) = sum of Manhattan dist to all base entries (cheap proxy, ignores walls)
    ents = base_entries()
    def phi(c):
        return sum(abs(c[0]-ex)+abs(c[1]-ey) for ex,ey in ents)
    cells.sort(key=phi)
    return cells[:960]


if __name__ == "__main__":
    analyze("2x3 blocks (current submission / SOTA shape)", layout_2x3_blocks())
    analyze("central cluster (ring road)", layout_central_cluster())
    analyze("diamond (min total-dist-to-bases)", layout_diamond())
