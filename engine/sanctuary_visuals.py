"""First native-32px sanctuary art pass, independent of collision and story logic."""
import math
import pygame

S = 32
PREFIX = "interior.sanctuary."


def paint_tile(surface, atlas, name, x, y):
    atlas.draw(surface, PREFIX + name, x, y)


def draw_room(surface, world, atlas, camera_x, camera_y, seconds):
    """Draw sanctuary art at 32px/native pixel scale. Camera is legacy 16px coordinates."""
    sx, sy = camera_x * 2, camera_y * 2
    for y, row in enumerate(world["tiles"]):
        for x, cell in enumerate(row):
            px, py = x * S - sx, y * S - sy
            if cell == "#":
                paint_tile(surface, atlas, "wall_trim" if y in (1, 13) else "stone_wall", px, py)
            else:
                paint_tile(surface, atlas, "floor_variant" if (x * 3 + y) % 9 == 0 else "floor", px, py)

    # Architectural details use the same native-resolution atlas as floor.
    for wx in (5, 16):
        paint_tile(surface, atlas, "window", wx * S - sx, 2 * S - sy)
    for xx in range(3, 19):
        if xx not in (5, 16):
            paint_tile(surface, atlas, "beam", xx * S - sx, S - sy)

    # Subtle central woven runner and a devotional mosaic.
    for y in range(6, 11):
        paint_tile(surface, atlas, "rug", 10 * S - sx, y * S - sy)
        paint_tile(surface, atlas, "rug", 11 * S - sx, y * S - sy)
    paint_tile(surface, atlas, "motif", 10 * S - sx, 5 * S - sy)

    props = {"altar": "altar", "table": "table", "bookshelf": "bookshelf", "door": "door"}
    for obj in world["objects"]:
        kind = props.get(obj["kind"])
        if kind is None:
            continue
        for dy in range(obj["h"]):
            for dx in range(obj["w"]):
                tx = obj["x"] + dx
                ty = obj["y"] + dy
                # For large furniture use readable repeated modules, not stretched pixels.
                paint_tile(surface, atlas, kind, tx * S - sx, ty * S - sy)

    paint_tile(surface, atlas, "candles", 9 * S - sx, 5 * S - sy)
    paint_tile(surface, atlas, "flowers", 3 * S - sx, 5 * S - sy)
    paint_tile(surface, atlas, "bench", 6 * S - sx, 11 * S - sy)
    paint_tile(surface, atlas, "planks", 18 * S - sx, 8 * S - sy)
    draw_sunlight(surface, sx, sy, seconds)


def draw_sunlight(surface, sx, sy, seconds):
    """Integer-pixel, gently breathing alpha shafts. No smooth upsampling."""
    light = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    # The bright panes are on the northern wall, projecting toward the room.
    pulse = int(4 * math.sin(seconds * 0.7))
    for window_x in (5, 16):
        px = (window_x + .5) * S - sx
        top = 3 * S - sy
        # Broad pale gold ambient shaft, then smaller vivid highlight.
        pygame.draw.polygon(light, (246, 204, 125, 25 + pulse), [
            (px - 9, top), (px + 12, top),
            (px + 100, top + 180), (px + 30, top + 180)])
        pygame.draw.polygon(light, (255, 227, 156, 21 + pulse), [
            (px - 3, top), (px + 6, top),
            (px + 77, top + 150), (px + 40, top + 150)])
        # Glint of sunlight on worn stone, not an opaque white flood.
        pygame.draw.ellipse(light, (242, 205, 133, 28 + pulse),
                            (round(px + 35), round(top + 125), 76, 24))
    # Stable slow motes; coordinates repeat, avoiding frame-to-frame noise.
    for i in range(10):
        bx = (i * 67 + 41) % 440 + 65 - sx // 5
        by = (i * 49 + 83 - int(seconds * (2 + i % 3))) % 215 + 90 - sy // 8
        pygame.draw.rect(light, (249, 231, 172, 60), (bx, by, 2, 2))
    surface.blit(light, (0, 0))
