"""Sanctuary V2 art pass; world collision remains map-based."""
from pathlib import Path
import math

import pygame

S = 32
# Windows and sunlight share one world-space origin, avoiding independent offsets.
WINDOW_X = (128, 432)
ASSET_ROOT = Path(__file__).resolve().parents[1] / "assets/atlases/interiors"
_CACHE = {}


def get(name):
    if name not in _CACHE:
        _CACHE[name] = pygame.image.load(str(ASSET_ROOT / (name + ".png"))).convert_alpha()
    return _CACHE[name]


def faded(name, opacity):
    """Scale authored alpha without replacing its transparent matte."""
    image = get(name).copy()
    image.fill((255, 255, 255, round(255 * opacity)), special_flags=pygame.BLEND_RGBA_MULT)
    return image


def draw_room(surface, world, atlas, camera_x, camera_y, seconds):
    """Render authored Sanctuary V2 layers at native 640x448 presentation scale."""
    sx, sy = round(camera_x * 2), round(camera_y * 2)

    def put(name, x, y):
        surface.blit(get(name), (round(x - sx), round(y - sy)))

    for y, row in enumerate(world["tiles"]):
        for x, cell in enumerate(row):
            if cell == "#":
                put("wall_stone" if y < 2 or y > 12 else "wall_dark", x * S, y * S)
            else:
                selector = (x * 13 + y * 7) % 17
                put("floor_worn" if selector == 0 else
                    "floor_b" if selector in (3, 11) else "floor_a", x * S, y * S)

    for x in WINDOW_X:
        put("window_sun", x, 8)
    put("timber", 24, 0)
    put("timber", 596, 0)
    put("altar", 225, 15)
    put("bookshelf", 487, 44)
    put("bookshelf", 556, 44)
    put("communal_table", 85, 237)
    put("bench", 97, 318)
    put("writing_desk", 451, 252)
    put("rug_small", 470, 302)
    put("rug_runner", 320, 170)
    put("flowers", 55, 159)
    put("plant", 579, 255)
    put("banner", 30, 37)
    # Preserve the map doorway at x=10..11, y=14..15.
    put("door", 10 * S - 16, 13 * S)

    breathe = 0.88 + 0.08 * math.sin(seconds * 0.55)
    for window_x in WINDOW_X:
        beam = faded("beam", breathe)
        surface.blit(beam, (round(window_x + 14 - sx), round(103 - sy)))
    for px, py in ((WINDOW_X[0] + 30, 230), (WINDOW_X[1] + 30, 245)):
        glow = faded("glow", (100 + 12 * math.sin(seconds * 1.3 + px)) / 255)
        surface.blit(glow, (round(px - sx), round(py - sy)))
    motes = faded("motes", 65 / 255)
    surface.blit(motes, (round(166 - sx), round(154 - sy + 5 * math.sin(seconds * 0.2))))
