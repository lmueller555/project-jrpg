"""Eldenmere's original, deterministic pixel-art environment pass.

All textures are drawn at native logical resolution and cached into surfaces.
Geometry and collision remain sourced from map JSON and the game runtime.
"""
import pygame

TILE = 16

INK = "#283b3b"
GRASS = ("#56854b", "#639350", "#79a559", "#3e6b44")
SOIL = ("#b49b6d", "#c4ac7d", "#9c805c", "#e0c495")
STONE = ("#85867d", "#aaa99a", "#696f6c", "#d5c4a3")
WATER = ("#306a8b", "#387b98", "#5da2ac", "#a4cbbe")
WOOD = ("#664b3c", "#92674a", "#c18a5d", "#d8b07a")


def box(s, c, x, y, w, h):
    pygame.draw.rect(s, c, (int(x), int(y), int(w), int(h)))


def line(s, c, a, b, thickness=1):
    pygame.draw.line(s, c, a, b, thickness)


def seed(x, y, salt=0):
    """Repeatable coordinate hash: no frame-to-frame visual noise."""
    n = (x * 374761393 + y * 668265263 + salt * 1442695041) & 0xffffffff
    n = ((n ^ (n >> 13)) * 1274126177) & 0xffffffff
    return n ^ (n >> 16)


def tile_art(kind, tx, ty):
    s = pygame.Surface((TILE, TILE))
    v = seed(tx, ty)
    if kind == "grass":
        s.fill(GRASS[v % 3])
        for n in range(3):
            x, y = (v >> (n * 5)) % 13 + 1, (v >> (n * 7 + 4)) % 12 + 2
            line(s, GRASS[3], (x, y + 2), (x + 1, y - 1))
            box(s, GRASS[2], x + 2, y, 2, 1)
        if v % 13 == 0:
            box(s, "#e6cd86", 9, 7, 2, 2)
            box(s, "#f0e2ac", 10, 6, 1, 1)
    elif kind == "path":
        s.fill(SOIL[0])
        for i in range(5):
            x, y = (v >> (i * 3)) % 14, (v >> (i * 5 + 1)) % 14
            box(s, SOIL[2 if i % 2 else 1], x, y, 2 + i % 2, 1)
        line(s, SOIL[3], (0, 0), (15, 0))
    elif kind == "farmland":
        s.fill("#5f6040")
        for y in range(2, 16, 5):
            line(s, "#957348", (0, y), (15, y), 2)
            line(s, "#3f7345", (0, y + 2), (15, y + 2))
            for x in range((tx % 2) * 3, 16, 7):
                box(s, "#9fb45d", x, y + 1, 2, 3)
    elif kind == "water":
        s.fill(WATER[v % 2])
        for y in (4, 11):
            x = (v >> y) % 6
            line(s, WATER[2], (x, y), (min(x + 6, 15), y))
            box(s, WATER[3], x + 2, y, 2, 1)
    elif kind == "bridge":
        s.fill("#51483f")
        for y in range(0, 16, 4):
            box(s, "#ae9570", 0, y, 16, 3)
            line(s, "#e1c194", (0, y), (15, y))
        box(s, "#524b42", 0, 0, 1, 16)
        box(s, "#524b42", 15, 0, 1, 16)
    elif kind == "trees":
        s.fill("#305940")
        box(s, "#4b3e34", 7, 10, 3, 6)
        pygame.draw.circle(s, "#284f39", (9, 8), 8)
        pygame.draw.circle(s, "#3d7545", (7, 6), 6)
        box(s, "#6da054", 4, 3, 4, 2)
        box(s, "#79a95c", 10, 6, 3, 2)
        box(s, "#295d3c", 11, 11, 4, 2)
    elif kind == "wall":
        s.fill("#545c61")
        for y in range(1, 16, 6):
            line(s, "#848b86", (0, y), (15, y))
            box(s, "#38434b", (tx % 2) * 6 + 3, y + 1, 1, 4)
    elif kind == "floor":
        s.fill("#9b8873")
        for y in range(0, 16, 8):
            line(s, "#71675c", (0, y), (15, y))
            box(s, "#c0aa89", 2 + (tx % 3) * 3, y + 2, 4, 1)
    else:
        s.fill("#db34cf")
    return s


def draw_tile(surface, cache, kind, x, y, tx, ty):
    key = (kind, tx % 13, ty % 11)
    if key not in cache:
        cache[key] = tile_art(kind, tx, ty)
    surface.blit(cache[key], (x, y))


def building(surface, obj, r):
    kind = obj["kind"]
    if kind == "sanctuary":
        roof, ridge = "#566a78", "#a8b9bb"
    elif kind == "mill":
        roof, ridge = "#7f503f", "#c88c66"
    else:
        roof, ridge = "#8b584e", "#d69a71"
    # Shaded plinth, stone foundation and warm timbered façade.
    box(surface, "#344542", r.x + 3, r.bottom, r.w - 1, 5)
    box(surface, "#656963", r.x, r.y + 8, r.w, r.h - 8)
    box(surface, "#c3ac8a", r.x + 4, r.y + 12, r.w - 8, r.h - 16)
    for bx in range(r.x + 8, r.right - 4, 21):
        box(surface, "#825f46", bx, r.y + 14, 3, r.h - 18)
    for by in range(r.y + 25, r.bottom - 6, 22):
        line(surface, "#ac9274", (r.x + 5, by), (r.right - 5, by))
    # Roof silhouette: stepped eaves, not a single flat rectangle.
    pygame.draw.polygon(surface, INK, [(r.x - 6, r.y + 12),
        (r.x + 10, r.y - 10), (r.right - 10, r.y - 10),
        (r.right + 6, r.y + 12)])
    pygame.draw.polygon(surface, roof, [(r.x - 3, r.y + 10),
        (r.x + 12, r.y - 8), (r.right - 12, r.y - 8),
        (r.right + 3, r.y + 10)])
    line(surface, ridge, (r.x + 12, r.y - 7), (r.right - 12, r.y - 7), 2)
    for px in range(r.x + 10, r.right - 4, 13):
        line(surface, "#a67963" if kind != "sanctuary" else "#77929d",
             (px, r.y + 1), (px + 8, r.y + 1))
    # Small windows and visible door footprint.
    for wx in (r.x + 13, r.right - 20):
        box(surface, "#393f43", wx - 1, r.bottom - 29, 12, 14)
        box(surface, "#9dc2b8", wx + 1, r.bottom - 27, 8, 9)
        box(surface, "#e1c690", wx + 1, r.bottom - 27, 3, 4)
        box(surface, "#c5ac8d", wx - 2, r.bottom - 16, 14, 3)
    box(surface, "#4c413a", r.centerx - 8, r.bottom - 22, 16, 22)
    box(surface, "#8f684b", r.centerx - 6, r.bottom - 20, 12, 20)
    box(surface, "#e4bc72", r.centerx + 3, r.bottom - 12, 2, 2)
    if kind == "sanctuary":
        # Architectural feature for the largest village landmark.
        box(surface, "#8c9598", r.centerx - 9, r.y - 20, 18, 17)
        box(surface, "#b8b8a7", r.centerx - 7, r.y - 18, 14, 13)
        box(surface, "#d5c29a", r.centerx - 2, r.y - 15, 4, 10)
    if kind == "mill":
        cx, cy = r.right + 1, r.centery + 6
        pygame.draw.circle(surface, "#493b31", (cx, cy), 16, 4)
        pygame.draw.circle(surface, "#b38d60", (cx, cy), 13, 2)
        for a in range(8):
            import math
            angle = a * math.tau / 8
            x2, y2 = int(cx + math.cos(angle) * 14), int(cy + math.sin(angle) * 14)
            line(surface, "#d3ab76", (cx, cy), (x2, y2), 2)
        pygame.draw.circle(surface, "#443e36", (cx, cy), 4)


def draw_object(surface, obj, ox, oy):
    k = obj["kind"]
    r = pygame.Rect(obj["x"] * TILE - ox, obj["y"] * TILE - oy,
                    obj["w"] * TILE, obj["h"] * TILE)
    if k in ("house", "mill", "sanctuary"):
        building(surface, obj, r)
    elif k == "well":
        box(surface, "#38494d", r.x - 2, r.y + 4, r.w + 4, r.h - 2)
        box(surface, "#a1a69b", r.x, r.y, r.w, r.h - 5)
        box(surface, "#305a73", r.x + 5, r.y + 6, r.w - 10, r.h - 14)
        box(surface, "#cad0ba", r.x + 2, r.y + 3, r.w - 4, 3)
    elif k == "shrine":
        box(surface, "#626767", r.x + 2, r.y + 9, r.w - 4, r.h - 9)
        box(surface, "#a9a69b", r.x + 7, r.y + 10, r.w - 14, r.h - 15)
        pygame.draw.polygon(surface, "#56677a", [(r.x, r.y + 12),
            (r.centerx, r.y - 4), (r.right, r.y + 12)])
        box(surface, "#d6c18a", r.centerx - 3, r.y + 17, 6, 9)
    elif k in ("altar", "table"):
        box(surface, "#594a41", r.x + 2, r.y + 5, r.w - 4, r.h - 5)
        box(surface, "#b28b66", r.x, r.y, r.w, 9)
        line(surface, "#e2ba8c", (r.x + 3, r.y + 2), (r.right - 4, r.y + 2), 2)
    elif k == "bookshelf":
        box(surface, "#594334", r.x, r.y, r.w, r.h)
        for yy in range(r.y + 4, r.bottom - 2, 12):
            box(surface, "#aa8255", r.x + 2, yy + 7, r.w - 4, 2)
            for xx in range(r.x + 5, r.right - 3, 7):
                box(surface, ("#b97e56", "#728c85", "#c1a16a")[xx % 3],
                    xx, yy, 4, 7)
    elif k == "door":
        box(surface, "#c59c69", r.x, r.y, r.w, 5)
        box(surface, "#70543e", r.x + 5, r.y + 5, r.w - 10, r.h - 5)
    elif k == "plaza":
        # Walkable civic stone ring; no collision alteration.
        for xx in range(r.x, r.right, 16):
            box(surface, "#baa98b", xx, r.y, 15, 2)
            box(surface, "#baa98b", xx, r.bottom - 2, 15, 2)
        for yy in range(r.y, r.bottom, 16):
            box(surface, "#baa98b", r.x, yy, 2, 15)
            box(surface, "#baa98b", r.right - 2, yy, 2, 15)


def avatar(surface, x, y, coat, phase=0):
    x, y = int(x), int(y)
    left, top = x - 8, y - 23
    pygame.draw.ellipse(surface, "#314b43", (left + 2, y - 3, 12, 3))
    # Asymmetrical walking feet and subtle cape shadow.
    box(surface, "#3a3538", left + 3, top + 13, 11, 7)
    box(surface, "#43382f", left + 4, top + 19 + phase, 4, 4 - phase)
    box(surface, "#43382f", left + 10, top + 19 - phase, 4, 4 + phase)
    box(surface, coat, left + 3, top + 10, 11, 10)
    box(surface, "#e0ba88", left + 2, top + 12, 2, 6)
    box(surface, "#e0ba88", left + 14, top + 12, 2, 6)
    box(surface, "#e5ba8b", left + 4, top + 3, 9, 8)
    box(surface, "#77543f", left + 3, top + 1, 11, 4)
    box(surface, "#5b4339", left + 3, top + 3, 3, 5)
    box(surface, "#262d34", left + 6, top + 8, 1, 1)
    box(surface, "#262d34", left + 11, top + 8, 1, 1)
    box(surface, "#e0d4af", left + 8, top + 12, 2, 5)
