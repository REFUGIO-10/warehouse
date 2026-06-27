"""Generate candidate layout JSONs for the optimization sprint.

Each generator returns exactly-960 unique shelf cells in 1..50, off the base-entry
cells, with every block <=2 wide in one dimension (so every shelf has an EMPTY
neighbour for pickup). Validity is checked by the official validator before write.

  python tools/gen_layouts.py            # write all to scratchpad/layouts/
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_KIT = Path(__file__).resolve().parent.parent / "refugio-starter-kit"
if str(_KIT) not in sys.path:
    sys.path.insert(0, str(_KIT))

from warehouse.layout import LayoutValidationError, validate_submitted_layout  # noqa: E402

OUT = Path("/private/tmp/claude-501/-Users-jose-jenarvaezg-REFUGIO-warehouse/"
           "40a775d5-3ba7-4524-8ac9-b1bb4edf5b02/scratchpad/layouts")


def _base_entry_cells() -> set[tuple[int, int]]:
    e: set[tuple[int, int]] = set()
    for x in range(3, 50, 2):
        e.add((x, 1))
    for x in range(2, 49, 2):
        e.add((x, 50))
    for y in range(2, 49, 2):
        e.add((1, y))
    for y in range(3, 50, 2):
        e.add((50, y))
    return e


ENTRIES = _base_entry_cells()


def _trim_to_960(cells: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Drop base-entry cells, then evenly remove the surplus to land on 960."""
    cells = [c for c in cells if c not in ENTRIES]
    n = len(cells)
    extra = n - 960
    if extra < 0:
        raise ValueError(f"only {n} cells, need 960")
    if extra == 0:
        return cells
    removed: set[int] = set()
    for k in range(extra):
        idx = (k * n) // extra + n // (2 * extra)
        while idx in removed:
            idx = (idx + 1) % n
        removed.add(idx)
    return [c for i, c in enumerate(cells) if i not in removed]


def blocks(block_w: int, block_h: int, aisle: int = 1, margin: int = 2) -> list[tuple[int, int]]:
    lo, hi = 1 + margin, 50 - margin
    px, py = block_w + aisle, block_h + aisle
    cells: list[tuple[int, int]] = []
    x = lo
    while x <= hi:
        y = lo
        while y <= hi:
            for cx in range(x, min(x + block_w, hi + 1)):
                for cy in range(y, min(y + block_h, hi + 1)):
                    cells.append((cx, cy))
            y += py
        x += px
    return _trim_to_960(cells)


def blocks_highways(block_w: int, block_h: int, every: int, margin: int = 2) -> list[tuple[int, int]]:
    """2xN blocks with 1-cell aisles, but every `every`-th vertical aisle widened
    to 2 cells (a passing highway). Compensate footprint with a smaller margin."""
    lo, hi = 1 + margin, 50 - margin
    cells: list[tuple[int, int]] = []
    x = lo
    col = 0
    while x <= hi:
        y = lo
        while y <= hi:
            for cx in range(x, min(x + block_w, hi + 1)):
                for cy in range(y, min(y + block_h, hi + 1)):
                    cells.append((cx, cy))
            y += block_h + 1
        aisle = 2 if (col % every == every - 1) else 1
        x += block_w + aisle
        col += 1
    return _trim_to_960(cells)


GENERATORS = {
    "blocks_2x2": lambda: blocks(2, 2, 1, 2),
    "blocks_2x3": lambda: blocks(2, 3, 1, 2),
    "blocks_3x2": lambda: blocks(3, 2, 1, 2),
    "blocks_2x4": lambda: blocks(2, 4, 1, 2),
    "blocks_4x2": lambda: blocks(4, 2, 1, 2),
    "blocks_2x2_m1": lambda: blocks(2, 2, 1, 1),
    "hw_2x3_every3": lambda: blocks_highways(2, 3, 3, 1),
    "hw_2x2_every4": lambda: blocks_highways(2, 2, 4, 1),
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, gen in GENERATORS.items():
        try:
            shelves = [[x, y] for (x, y) in gen()]
            layout = {"schema_version": 1, "shelves": shelves}
            validate_submitted_layout(layout)
        except (LayoutValidationError, ValueError) as exc:
            print(f"  {name:<18} INVALID: {exc}")
            continue
        path = OUT / f"{name}.json"
        path.write_text(json.dumps(layout))
        print(f"  {name:<18} OK  shelves={len(shelves)}  -> {path.name}")


if __name__ == "__main__":
    main()
