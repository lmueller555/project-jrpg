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


def clean_sunbeam():
    """Build a transparent light-only overlay, excluding the source image's dark matte."""
    if "clean_beam" not in _CACHE:
        source = get("beam")
        result = pygame.Surface(source.get_size(), pygame.SRCALPHA)
        width, height = source.get_size()
        for y in range(height):
            for x in range(width):
                r, g, b, a = source.get_at((x, y))
                # The source is a cutout of a concept sheet with a dark
                # background: draw only its warm luminous pixels.
                luminance = (r * 299 + g * 587 + b * 114) // 1000
                warmth = max(0, min(r - b, g - b))
                strength = max(0, min(255, (luminance - 78) * 2, warmth * 3))
                if a > 0 and strength > 0:
                    result.set_at((x, y), (255, 215, 134, min(a, strength)))
        _CACHE["clean_beam"] = result
    return _CACHE["clean_beam"]


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

    breathe = 0.20 + 0.035 * math.sin(seconds * 0.55)
    for window_x in WINDOW_X:
        beam = clean_sunbeam().copy()
        beam.set_alpha(round(255 * breathe))
        surface.blit(beam, (round(window_x + 14 - sx), round(103 - sy)))
    for px, py in ((WINDOW_X[0] + 30, 230), (WINDOW_X[1] + 30, 245)):
        glow = get("glow").copy()
        glow.set_alpha(round(100 + 12 * math.sin(seconds * 1.3 + px)))
        surface.blit(glow, (round(px - sx), round(py - sy)))
    motes = get("motes").copy()
    motes.set_alpha(65)
    surface.blit(motes, (round(166 - sx), round(154 - sy + 5 * math.sin(seconds * 0.2))))
