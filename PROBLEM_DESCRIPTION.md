# 01 OBJECTIVE

Each team submits a single Python file that defines two things: the warehouse **shelf layout** and the robot **policy**. The evaluator runs 96 robots for 300 ticks across three hidden official seeds and counts completed deliveries. Your **raw score** is the total number of deliveries summed over every seed.

```math
raw_score = \sum_{s \in seeds} deliveries(create_layout(), act, s)
```

Hackathon points are **not** the raw score. They are awarded only when your submission pushes the public performance frontier - see section 09.

Local runs use a public representative seed for smoke testing. The official evaluation uses three hidden seeds, fixed by the organizers and identical for every team; they are not exposed to your policy or shown in the public job results.

---

# 02 THE WAREHOUSE

The warehouse is a fixed **52 x 52** grid. Coordinates are written `[x, y]`: `x` increases left -> right, `y` increases top -> bottom. The top-left cell is `[0, 0]`; the bottom-right is `[51, 51]`.

The walkable floor is the **50 x 50** interior, where `1 <= x <= 50` and `1 <= y <= 50`. The outer border (`x=0`, `x=51`, `y=0`, `y=51`) holds the 96 fixed bases.

* **Empty** - walkable corridor
* **Shelf** - impassable storage
* **Base** - fixed external dock
* **Robot** - Target

The official starter layout. A robot leaves its base, reaches a cell adjacent to its target shelf, picks up, and returns to its base-entry cell to drop.

The 96 bases are fixed and **not** part of your layout - you cannot move them. Robots are assigned by side, in this id order: top, then bottom, then left, then right. Each robot starts and drops on the single interior cell adjacent to its base.

```text
Top robot_id 0..23 base (x, 0) for x = 3, 5, 7, ..., 49
Bottom robot_id 24..47 base (x, 51) for x = 2, 4, 6, ..., 48
Left robot_id 48..71 base (0, y) for y = 2, 4, 6, ..., 48
Right robot_id 72..95 base (51, y) for y = 3, 5, 7, ..., 49
```

---

# 03 SUBMISSION FILE

Your submission is a **single Python file** that defines exactly two functions. Import only from `warehouse_api` - everything else is provided.

### CREATE_LAYOUT()

Returns your shelf layout as a JSON-like dict. Must produce exactly 960 unique shelf coordinates inside the interior (`1 <= x <= 50`, `1 <= y <= 50`). Must be **deterministic** - the evaluator calls it more than once and rejects layouts that change between calls. Setup time counts against your policy budget.

```python
def create_layout() -> dict[str, object]:
    shelves = []
    for x0 in range(3, 48, 4):
        for y0, y1 in ((3, 12), (15, 24),
                       (27, 36), (39, 48)):
            for x in (x0, x0 + 1):
                for y in range(y0, y1 + 1):
                    shelves.append([x, y])
    # Must be exactly 960 shelves
    return {"schema_version": 1, "shelves": shelves}
```

### ACT(OBSERVATION)

Called **once per robot per tick** (96 robots x 300 ticks). Receives an `Observation` with the robot's state and returns one `Action`. No shared memory between robots or ticks - the function must be pure and stateless.

```python
def act(observation: Observation) -> Action:
    # Not carrying? Go pick up from target shelf.
    if not observation.carrying_item:
        # Navigate toward target_item_position...
        # When adjacent, return Action.PICKUP
        return Action.RIGHT  # placeholder

    # Carrying? Go deliver at your base.
    else:
        # Navigate toward base_position...
        # When at base-entry cell, return Action.DROP
        return Action.LEFT  # placeholder
```

### OBSERVATION FIELDS

Each call to `act()` receives an `Observation` with these fields. You can see every robot's position, but not their targets or carrying status.

* `observation.tick` - current simulation tick (0-299)
* `observation.robot_id` - this robot's ID (0-95)
* `observation.position` - (x, y) where you are now
* `observation.base_position` - (x, y) of your home base on the perimeter
* `observation.target_item_position` - (x, y) of the shelf you must pick up from
* `observation.carrying_item` - True if you are carrying a package
* `observation.grid` - 2D grid of `CellType.EMPTY` / `CellType.SHELF` / `CellType.BASE`
* `observation.all_robot_positions` - dict mapping every `robot_id` -> (x, y)

### AVAILABLE ACTIONS

* `Action.UP` / `DOWN` / `LEFT` / `RIGHT` - move one cell in that direction
* `Action.PICKUP` - grab the item from your target shelf (must be adjacent, not already carrying)
* `Action.DROP` - deliver the item at your base-entry cell (must be carrying, at the right cell)
* `Action.WAIT` - do nothing this tick (also the fallback if your function raises an exception)

---

# 04 LAYOUT RULES

* **EXACTLY 960 SHELVES:** The returned list must contain exactly 960 shelf coordinates. No more, no less.
* **TWO-INTEGER COORDINATES:** Each entry is an [x, y] pair of integers, e.g. [12, 34].
* **UNIQUE CELLS:** No coordinate may repeat. Duplicates invalidate the whole layout.
* **INTERIOR ONLY:** Every shelf must satisfy 1 <= x <= 50 and 1 <= y <= 50. The outer border is reserved for bases.
* **BASE ENTRIES OPEN:** You cannot place a shelf on the interior cell adjacent to any base. Robots need that cell to enter and drop.
* **CARDINAL PICKUP ACCESS:** Every shelf must have at least one orthogonally adjacent walkable cell. Diagonals do not count.
* **ONE CONNECTED FLOOR:** All empty interior cells must form a single connected region under up/down/left/right moves. No sealed pockets.

```text
schema_version == 1
len(shelves) == 960 and len(set(shelves)) == 960
every [x, y]: x, y integers with 1 <= x <= 50 and 1 <= y <= 50
base-entry cells stay empty · floor stays connected · each shelf reachable
```

Targets are sampled from your submitted shelves, so **every** shelf must be reachable. Shelf order does not matter: the evaluator normalizes the list into a deterministic row-major order before generating targets. Think of a layout as a set of 960 cells.

### TWO VALID LAYOUTS, VERY DIFFERENT GEOMETRY

**Canonical rack blocks** - dense, predictable, prone to corridor congestion.

```python
def create_layout() -> dict[str, object]:
    # Canonical rack blocks: 12 two-wide columns,
    # four vertical bands, regular service aisles.
    shelves: list[list[int]] = []
    for x0 in range(3, 48, 4):
        for y0, y1 in ((2, 12), (15, 24), (27, 36), (39, 48)):
            for x in (x0, x0 + 1):
                for y in range(y0, y1 + 1):
                    shelves.append([x, y])
    return {"schema_version": 1, "shelves": shelves}
```

**Wide avenues** - broad north-south corridors, but longer local detours.

```python
def create_layout() -> dict[str, object]:
    # Wide avenues: fewer, taller rack walls with
    # broad north-south corridors between them.
    shelves: list[list[int]] = []
    for x0 in (4, 8, 12, 17, 22, 27, 32, 36, 41, 45):
        for x in (x0, x0 + 1):
            for y in range(2, 50):
                shelves.append([x, y])
    return {"schema_version": 1, "shelves": shelves}
```

These are teaching examples, not recommended optima. The layout is part of the search space - redesign the geometry freely.

---

# 05 ROBOT CYCLE

1. **FIND TARGET:** Each robot is born empty with a target shelf. Navigate to any empty cell orthogonally adjacent to that shelf.
2. **PICKUP:** Emit `Action.PICKUP` from any adjacent walkable cell. There is no shelf direction rule. The shelf is then locked until you drop.
3. **RETURN HOME:** Carry the package to the single walkable cell adjacent to your own base.
4. **DROP:** Emit `Action.DROP`. A successful drop scores +1 delivery and assigns a fresh target shelf. Repeat forever.

---

# 06 OBSERVATION

Policies are decentralized and memoryless. A robot sees the full static map and **all** current robot positions, but it only knows its **own** target, base, and carrying state. You see where everyone is, but not what they intend to do.

| Field | Description |
| --- | --- |
| `tick` | Current simulation tick, starting at 0. |
| `robot_id` | ID of the robot being controlled, 0-95. |
| `position` | This robot's current interior (x, y). |
| `base_position` | This robot's fixed external base cell. |
| `target_item_position` | The shelf this robot must pick up next. |
| `carrying_item` | True if this robot is currently carrying a package. |
| `grid` | Immutable view of the full static warehouse grid. |
| `all_robot_positions` | Every robot's position at the start of the tick. |

---

# 07 ACTIONS & COLLISIONS

Each call returns exactly one action: `UP`, `DOWN`, `LEFT`, `RIGHT`, `WAIT`, `PICKUP`, or `DROP`. `PICKUP` and `DROP` never move the robot - emit them on the tick you are already adjacent to the shelf or base. An invalid or exception-raising action becomes a blocked `WAIT` for that robot and tick.

Movement is resolved **simultaneously** for all 96 robots. No two robots may end on the same cell, and two robots may never swap across an edge. When moves conflict, the simulator deterministically blocks the moving robots needed to restore a valid state - blocked robots stay in place.

* **Edge swap:** A and B try to trade cells - both are blocked.
* **Vertex conflict:** Two robots target the same cell - both are blocked.
* **Following chain:** If the leader cannot move, the blocking cascades back.

---

# 08 TICK RESOLUTION

1. **BUILD OBSERVATIONS:** The simulator snapshots state and builds one Observation per robot. All robots see the same start-of-tick positions.
2. **CALL THE POLICY:** `act(observation)` is called once per robot and the requested action is recorded.
3. **STATIC VALIDITY:** Moves into a shelf, a base, or outside the walkable interior are rejected and become WAIT. WAIT is always valid.
4. **RESOLVE PICKUPS:** A PICKUP succeeds only if adjacent to your unlocked target shelf and not already carrying. Ties go to the lowest `robot_id`.
5. **RESOLVE DROPS:** A DROP on your own base-entry cell while carrying scores +1 delivery and assigns a new target.
6. **RESOLVE COLLISIONS:** Edge swaps are blocked for both robots; vertex conflicts are resolved to a fixpoint so blocked robots can cascade.
7. **APPLY & ADVANCE:** Item state updates are applied, new targets are issued, and the simulation advances to the next tick.

Because PICKUP/DROP consume the tick, a robot that moves adjacent to its target at tick t cannot pick up until tick t+1. Same for dropping at the base.

---

# 09 SCORING

**Raw deliveries** is the total number of completed deliveries summed across all hidden official seeds. It is the simulation result your hackathon points are computed from - but on its own it is not the ranking (see the frontier below).

Each job also reports two diagnostics: **blocked movement attempts** and the total **remaining Manhattan distance** from each robot to its next useful cell. They help you debug congestion and only break ties when ordering the raw-result table - they do **not** affect hackathon points.

### PROGRESSIVE FRONTIER (HACKATHON POINTS)

Points reward **pushing the public frontier**, not matching it. Early deliveries are easy; later ones are worth more. We use a **triangular-number bounty**: the k-th delivery above the starter baseline is worth k points.

Define the **triangular number**:

```math
T(n) = \frac{n(n + 1)}{2} = 1 + 2 + 3 + ... + n
```

Let C = 100 be the starter baseline, F the public frontier before your submission finishes, and D your raw deliveries. Then:

```math
previous = \max(F, C) \quad current = \max(D, C)
```

```math
points = \begin{cases} T(current - C) - T(previous - C) & \text{if } current > previous \\ 0 & \text{otherwise} \end{cases}
```

Expanding the subtraction, your bounty equals the sum of consecutive integers from (previous - C + 1) to (current - C):

```math
points = \sum_{k=previous-C+1}^{current-C} k
```

In plain words: the 1st delivery above the baseline is worth 1 point, the 50th is worth 50, the 100th is worth 100. A frontier jump earns the sum of every newly claimed slice.

### WORKED EXAMPLE

```math
C = 100, \quad F = 200, \quad D = 203
```

```math
previous = \max(200, 100) = 200, \quad current = \max(203, 100) = 203
```

```math
points = 101 + 102 + 103 = T(103) - T(100) = 306 \quad (\text{slices } 201-203)
```

Only the **first validated** job to claim a frontier slice earns those points. A later submission with the same score earns 0. A high raw score can still earn 0 hackathon points if it does not move the frontier - so submit early and often.

---

# 10 RUNTIME & LIMITS

Submissions run in an isolated sandbox (2 vCPU). The whole evaluation shares a **policy budget of 180 s** - the sum of import, `create_layout()`, and all `act()` calls across every seed - with a hard timeout of **240 s**. Exceeding the budget ends the run as `timed_out` and scores 0. The static map means precomputing distances once is far cheaper than re-searching every tick.

**THIRD-PARTY PACKAGES:**
`numpy`, `scipy`, `networkx`, `sortedcontainers`, `numba`

**PLUS A STANDARD-LIBRARY SUBSET:**
`array`, `bisect`, `collections`, `copy`, `dataclasses`, `enum`, `functools`, `hashlib`, `heapq`, `itertools`, `math`, `operator`, `queue`, `random`, `statistics`, `typing`, `warehouse_api`

* Self-contained: no reading or writing files (open is blocked).
* No network access (sockets, http, urllib, requests, ftplib).
* No subprocesses, threads, asyncio, or multiprocessing.
* No os / environment access, eval / exec / compile, or `__import__`.
* No importing private simulator modules (`warehouse.simulation`, `warehouse.state`).
* Deterministic only: any randomness must be derived purely from the observation.

Platform rules: max file size **256 KB**, valid team token required, a **30-minute cooldown** after a successful submission, and up to **3 failed attempts** within a 30-minute window (each failure expires after 30 minutes).

**Rule 1 - If it runs, it counts.** If your submission compiles, executes, and produces a score - it is valid. There are no subjective disqualifications. Any approach that the sandbox runs successfully counts.

**Rule 2 - No external help.** Only your registered team members may contribute. No outside collaborators, no asking someone who is not on your team.

Attempts at malware, sabotage, or illicit competition will be punished with immediate exclusion. We are here to have fun - don't be an asshole.

---

# 11 LOCAL TESTING

### VALIDATE

```bash
python -m warehouse.validate_layout \
  layout.json
```

Check a standalone layout JSON. Official submissions validate the object returned by `create_layout()` automatically.

### RUN LOCALLY

```bash
python -m warehouse.local_runner \
  my_submission.py \
  --ticks 300
```

Validates your layout, then runs the policy locally for 300 ticks. Use this for smoke testing before submitting - official scoring uses hidden seeds instead.

### GENERATE A REPLAY

```bash
python -m warehouse.eval_runner \
  my_submission.py \
  --replay-seed round-0 \
  --replay-out outputs/replay.json
```

Open the replay in the viewer to see where robots jam on a representative run, then refine your layout and policy.
