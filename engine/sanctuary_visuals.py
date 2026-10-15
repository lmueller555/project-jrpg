"""Sanctuary architectural composition with reusable map-derived geometry."""
from pathlib import Path
import math
import pygame

from engine.architecture import resolve_architecture, PRESENTATION_TILE

S = PRESENTATION_TILE
ASSET_ROOT = Path(__file__).resolve().parents[1] / "assets/atlases/interiors"
_CACHE = {}


def get(name):
    if name not in _CACHE:
        _CACHE[name] = pygame.image.load(str(ASSET_ROOT / (name + ".png"))).convert_alpha()
    return _CACHE[name]


def _blit(surface, name, x, y, sx, sy):
    surface.blit(get(name), (round(x - sx), round(y - sy)))


def _sunlight(surface, layout, sx, sy, seconds):
    """Transparent, bounded, window-anchored light; no opaque beam matte."""
    for opening in layout.windows:
        center = opening.x + opening.width // 2
        start_x = center + 2 - sx
        start_y = opening.y + 55 - sy
        strength = int(14 + 3 * math.sin(seconds * 0.55))
        glow = pygame.Surface((130, 190), pygame.SRCALPHA)
        pygame.draw.polygon(glow, (255, 204, 113, strength),
                            [(17, 0), (43, 0), (122, 190), (0, 190)])
        pygame.draw.polygon(glow, (255, 232, 156, strength // 2),
                            [(22, 0), (36, 0), (96, 190), (22, 190)])
        surface.blit(glow, (round(start_x - 27), round(start_y)))


def draw_room(surface, world, atlas, camera_x, camera_y, seconds):
    """Render architecture at native presentation scale, map/collision untouched."""
    layout = resolve_architecture(world)
    sx, sy = round(camera_x * 2), round(camera_y * 2)
    for y, row in enumerate(world["tiles"]):
        for x, symbol in enumerate(row):
            px, py = x * S, y * S
            if (x, y) in layout.wall_cells:
                name = "wall_stone" if y < 2 or y >= 13 else "wall_dark"
            else:
                selector = (x * 13 + y * 7) % 17
                name = ("floor_worn" if selector == 0 else
                        "floor_b" if selector in (3, 11) else "floor_a")
            _blit(surface, name, px, py, sx, sy)

    # Clean continuous wall/baseboard transitions following actual north edge.
    for x, y, dx, dy in sorted(layout.floor_edges):
        if (dx, dy) == (0, -1) and y == 2:
            _blit(surface, "wall_stone", x * S, y * S - 12, sx, sy)

    # Tall windows are architectural alcoves: the rear 64px wall hosts
    # the top section, while the lower section is deliberate wall relief.
    for opening in layout.windows:
        _blit(surface, "wall_plaster", opening.x, opening.y + 48, sx, sy)
        _blit(surface, "wall_plaster", opening.x + S, opening.y + 48, sx, sy)
        _blit(surface, "window_sun", opening.x, opening.y, sx, sy)

    # Two timber structural supports aligned to wall boundaries.
    _blit(surface, "timber", S, 0, sx, sy)
    _blit(surface, "timber", layout.width - 2 * S, 0, sx, sy)
    _blit(surface, "altar", layout.width // 2 - 96, 15, sx, sy)
    _blit(surface, "bookshelf", layout.width - 6 * S, 44, sx, sy)
    _blit(surface, "bookshelf", layout.width - 4 * S, 44, sx, sy)
    _blit(surface, "communal_table", 85, 237, sx, sy)
    _blit(surface, "bench", 97, 318, sx, sy)
    _blit(surface, "writing_desk", layout.width - 7 * S - 3, 252, sx, sy)
    _blit(surface, "rug_small", layout.width - 6 * S - 10, 302, sx, sy)
    _blit(surface, "rug_runner", layout.width // 2 - 24, 170, sx, sy)
    _blit(surface, "flowers", 55, 159, sx, sy)
    _blit(surface, "plant", layout.width - 4 * S, 255, sx, sy)
    _blit(surface, "banner", 30, 37, sx, sy)

    # Door sprite is wider than collision aperture by a 16px surround each side.
    door = layout.door
    _blit(surface, "door", door.x - 16, door.y - 32, sx, sy)
    _sunlight(surface, layout, sx, sy, seconds)
    motes = get("motes").copy()
    motes.fill((255, 255, 255, 65), special_flags=pygame.BLEND_RGBA_MULT)
    surface.blit(motes, (round(layout.windows[0].x + 38 - sx),
                         round(154 - sy + 5 * math.sin(seconds * 0.2))))
