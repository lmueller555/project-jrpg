"""Project JRPG: first explorable Eldenmere vertical slice.

Run with: python -m pip install -r requirements.txt && python main.py
Original deterministic pixel-art pass; maps stay editable JSON.
"""
import json
import math
from pathlib import Path

import pygame
from visuals import avatar, draw_object, draw_tile

TILE = 16
VIEW_W, VIEW_H = 320, 224
SCALE = 3
SPEED = 88
ROOT = Path(__file__).resolve().parent

SOLID_TERRAIN = {"water", "trees", "wall"}
SOLID_OBJECTS = {"sanctuary", "house", "mill", "well", "shrine", "altar", "table", "bookshelf"}
FONT_NAME = None


def load_map(map_id):
    file_path = ROOT / ("maps/interiors/sanctuary.json" if map_id == "sanctuary_room"
                        else "maps/towns/eldenmere.json")
    with file_path.open(encoding="utf-8") as file:
        data = json.load(file)
    width = len(data["tiles"][0])
    assert data["tiles"] and all(len(row) == width for row in data["tiles"])
    return data


def object_rect(obj):
    return pygame.Rect(obj["x"] * TILE, obj["y"] * TILE, obj["w"] * TILE, obj["h"] * TILE)


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Project JRPG — Eldenmere World Slice")
        self.window = pygame.display.set_mode((VIEW_W * SCALE, VIEW_H * SCALE))
        self.canvas = pygame.Surface((VIEW_W, VIEW_H))
        self.font = pygame.font.Font(FONT_NAME, 12)
        self.small = pygame.font.Font(FONT_NAME, 10)
        self.clock = pygame.time.Clock()
        self.tile_cache = {}
        self.load("sanctuary_room")
        self.message = "Morning in Eldenmere. WASD / Arrows: move   E: interact"
        self.message_timer = 7

    def load(self, map_id):
        self.world = load_map(map_id)
        sx, sy = self.world["player_spawn"]
        self.x, self.y = (sx + 0.5) * TILE, (sy + 0.8) * TILE
        self.facing = (0, 1)
        self.phase = 0

    def blocked(self, x, y):
        # The collision footprint lives at the character's feet.
        foot = pygame.Rect(int(x - 4), int(y - 5), 8, 6)
        for cx, cy in [(foot.left, foot.top), (foot.right - 1, foot.top),
                       (foot.left, foot.bottom - 1), (foot.right - 1, foot.bottom - 1)]:
            tx, ty = cx // TILE, cy // TILE
            if not (0 <= ty < len(self.world["tiles"]) and
                    0 <= tx < len(self.world["tiles"][0])):
                return True
            if self.world["legend"][self.world["tiles"][ty][tx]] in SOLID_TERRAIN:
                return True
        for obj in self.world["objects"]:
            if obj["kind"] not in SOLID_OBJECTS:
                continue
            r = object_rect(obj)
            # Entrances are narrow clear spaces on buildings' southern walls.
            if "entrance" in obj:
                entry_x = (obj["entrance"][0] + 0.5) * TILE
                if abs(x - entry_x) <= 6 and y >= r.bottom - 18:
                    continue
            if foot.colliderect(r):
                return True
        return False

    def interact(self):
        tx = self.x + self.facing[0] * 18
        ty = self.y + self.facing[1] * 18
        for npc in self.world.get("npcs", []):
            nx, ny = (npc["x"] + .5) * TILE, (npc["y"] + .9) * TILE
            if math.hypot(self.x - nx, self.y - ny) < 27:
                self.say(f'{npc["name"]}: {npc["speech"]}')
                return
        for obj in self.world["objects"]:
            r = object_rect(obj)
            expanded = r.inflate(20, 20)
            if not expanded.collidepoint(tx, ty):
                continue
            if obj.get("transition") == "eldenmere":
                self.load("eldenmere")
                self.say("Eldenmere — a quiet mountain village.")
                return
            if obj.get("transition") == "sanctuary_room":
                self.load("sanctuary_room")
                self.say("Eldenmere Sanctuary")
                return
            self.say(obj.get("label", "An ordinary part of village life."))
            return
        self.say("Nothing unusual here.")

    def say(self, content):
        self.message, self.message_timer = content, 5

    def tick(self, dt):
        keys = pygame.key.get_pressed()
        dx = int(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - int(keys[pygame.K_a] or keys[pygame.K_LEFT])
        dy = int(keys[pygame.K_s] or keys[pygame.K_DOWN]) - int(keys[pygame.K_w] or keys[pygame.K_UP])
        if dx or dy:
            norm = math.hypot(dx, dy)
            dx, dy = dx / norm, dy / norm
            self.facing = (dx, dy)
            for axis, change in (("x", dx * SPEED * dt), ("y", dy * SPEED * dt)):
                nx, ny = (self.x + change, self.y) if axis == "x" else (self.x, self.y + change)
                if not self.blocked(nx, ny):
                    self.x, self.y = nx, ny
            self.phase = (self.phase + dt * 7) % 2
        else:
            self.phase = 0
        self.message_timer = max(0, self.message_timer - dt)

    def render(self):
        w = len(self.world["tiles"][0]) * TILE
        h = len(self.world["tiles"]) * TILE
        ox = max(0, min(int(self.x - VIEW_W / 2), max(0, w - VIEW_W)))
        oy = max(0, min(int(self.y - VIEW_H / 2), max(0, h - VIEW_H)))
        self.canvas.fill("#1b2530")
        min_x, max_x = max(0, ox // TILE), min(len(self.world["tiles"][0]), (ox + VIEW_W) // TILE + 2)
        min_y, max_y = max(0, oy // TILE), min(len(self.world["tiles"]), (oy + VIEW_H) // TILE + 2)
        for y in range(min_y, max_y):
            for x in range(min_x, max_x):
                char = self.world["tiles"][y][x]
                draw_tile(self.canvas, self.tile_cache, self.world["legend"][char], x * TILE - ox, y * TILE - oy, x, y)
        for obj in self.world["objects"]:
            draw_object(self.canvas, obj, ox, oy)
        for npc in self.world.get("npcs", []):
            avatar(self.canvas, (npc["x"] + .5) * TILE - ox, (npc["y"] + .9) * TILE - oy, npc["color"])
        avatar(self.canvas, self.x - ox, self.y - oy, "#637cbb", int(self.phase))
        pygame.draw.rect(self.canvas, "#172333", (0, 0, VIEW_W, 17))
        label = self.small.render(self.world["name"] + "  |  E interact  |  ESC quit", False, "#f5e5c9")
        self.canvas.blit(label, (6, 4))
        if self.message_timer:
            pygame.draw.rect(self.canvas, "#111a29", (4, VIEW_H - 34, VIEW_W - 8, 30))
            pygame.draw.rect(self.canvas, "#e1c996", (4, VIEW_H - 34, VIEW_W - 8, 30), 1)
            # Soft wrap rather than dropping text out of viewport.
            words, lines, line = self.message.split(), [], ""
            for word in words:
                proposed = (line + " " + word).strip()
                if self.small.size(proposed)[0] > VIEW_W - 22 and line:
                    lines.append(line)
                    line = word
                else:
                    line = proposed
            lines.append(line)
            for i, text in enumerate(lines[:2]):
                self.canvas.blit(self.small.render(text, False, "#f5e5c9"), (10, VIEW_H - 29 + i * 12))
        pygame.transform.scale(self.canvas, self.window.get_size(), self.window)
        pygame.display.flip()

    def run(self):
        running = True
        while running:
            dt = min(self.clock.tick(60) / 1000, 1 / 20)
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    running = False
                elif event.type == pygame.KEYDOWN and event.key in (pygame.K_e, pygame.K_SPACE):
                    self.interact()
            self.tick(dt)
            self.render()
        pygame.quit()


if __name__ == "__main__":
    Game().run()
