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
