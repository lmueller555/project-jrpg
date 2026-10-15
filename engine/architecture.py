"""Reusable, deterministic architectural layout from the existing map grid.

All coordinates are world-space presentation pixels. This module deliberately
has no pygame, asset, collision, or map-mutation dependencies.
"""
from dataclasses import dataclass

PRESENTATION_TILE = 32


@dataclass(frozen=True)
class Opening:
    kind: str
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class ArchitectureLayout:
    width: int
    height: int
    wall_cells: frozenset
    floor_cells: frozenset
    floor_edges: frozenset
    wall_corners: frozenset
    door: Opening
    windows: tuple


def resolve_architecture(world, *, tile=PRESENTATION_TILE):
    """Resolve structure from the map, without changing gameplay geometry.

    A 2-row north collision wall can host visually taller wall-mounted features:
    those extend into the room as alcoves, but never change collision.
    """
    rows = world["tiles"]
    if not rows or any(len(row) != len(rows[0]) for row in rows):
        raise ValueError("Architecture requires a rectangular map")
    width, height = len(rows[0]), len(rows)
    walls = frozenset((x, y) for y, row in enumerate(rows) for x, v in enumerate(row) if world["legend"][v] == "wall")
    floor = frozenset((x, y) for y, row in enumerate(rows) for x, v in enumerate(row) if world["legend"][v] == "floor")
    edges = frozenset((x, y, dx, dy) for (x, y) in floor for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)) if (x + dx, y + dy) in walls)
    corners = frozenset((x, y) for (x, y) in walls if any((x + dx, y) in floor for dx in (-1, 1)) and any((x, y + dy) in floor for dy in (-1, 1)))
    exits = [o for o in world.get("objects", []) if o.get("transition")]
    if len(exits) != 1:
        raise ValueError("Architecture expects exactly one authored entrance/exit")
    exit_obj = exits[0]
    door = Opening("door", exit_obj["x"] * tile, exit_obj["y"] * tile, exit_obj["w"] * tile, exit_obj["h"] * tile)

    # Two symmetrically authored window bays, computed from interior extents.
    north_floor = min(y for _, y in floor)
    interior_x = sorted(x for x, y in floor if y == north_floor)
    if len(interior_x) < 10:
        raise ValueError("Not enough north-wall span for paired windows")
    left, right = interior_x[0] * tile, (interior_x[-1] + 1) * tile
    span = right - left
    centers = (left + span // 4, left + 3 * span // 4)
    windows = tuple(Opening("window", c - tile, 0, tile * 2, tile * 4) for c in centers)
    return ArchitectureLayout(width * tile, height * tile, walls, floor, edges, corners, door, windows)
