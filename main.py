"""Project JRPG: first explorable Eldenmere vertical slice.

Run with: python -m pip install -r requirements.txt && python main.py
Original deterministic pixel-art pass; maps stay editable JSON.
"""
import json
import math
from pathlib import Path

import pygame
from visuals import avatar, draw_object, draw_tile
from engine.assets import AtlasRegistry, AnimationPlayer, RenderQueue
from engine.sanctuary_visuals import draw_room as draw_sanctuary_room
from engine.dialogue_ui import DialogueBox

TILE = 16
VIEW_W, VIEW_H = 320, 224
ART_SCALE = 2  # Legacy 16px tiles render as 32px tiles until native atlases replace them.
LOGICAL_W, LOGICAL_H = VIEW_W * ART_SCALE, VIEW_H * ART_SCALE
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
        self.fullscreen = True
        self.windowed_size = (960, 672)
        self.window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.canvas = pygame.Surface((VIEW_W, VIEW_H))
        self.world_canvas = pygame.Surface((LOGICAL_W, LOGICAL_H))
        self.overlay = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
        self.npc_sprites = {}
        self.dialogue = DialogueBox(ROOT / 'assets')
        self.font = pygame.font.Font(FONT_NAME, 12)
        self.small = pygame.font.Font(FONT_NAME, 10)
        self.clock = pygame.time.Clock()
        self.tile_cache = {}
        self.assets = AtlasRegistry(ROOT / 'assets')
        self.caelen_clips = {name: AnimationPlayer(self.assets, name) for name in self.assets.manifest['animations'] if name.startswith('caelen.')}
        self.water_clip = AnimationPlayer(self.assets, 'ambient.water')
        self.smoke_clip = AnimationPlayer(self.assets, 'ambient.smoke')
        self.walking = False
        self.ambient_time = 0.0
        self.load("sanctuary_room")
        self.message = "Morning in Eldenmere. WASD / Arrows: move   E: interact"
        self.message_timer = 0
        self.say("Morning in Eldenmere. WASD / Arrows: move   E: interact", speaker="Eldenmere Sanctuary")

    def load(self, map_id):
        self.world = load_map(map_id)
        sx, sy = self.world["player_spawn"]
        self.x, self.y = (sx + 0.5) * TILE, (sy + 0.8) * TILE
        self.facing = (0, 1)
        self.phase = 0
        self.walking = False

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
                self.say(npc["speech"], speaker=npc["name"], mode="character")
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

    def say(self, content, speaker="", mode="narration"):
        self.dialogue.show(content, speaker=speaker, mode=mode)
        self.message, self.message_timer = content, 0

    def tick(self, dt):
        keys = pygame.key.get_pressed()
        dx = int(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - int(keys[pygame.K_a] or keys[pygame.K_LEFT])
        dy = int(keys[pygame.K_s] or keys[pygame.K_DOWN]) - int(keys[pygame.K_w] or keys[pygame.K_UP])
        self.walking = bool(dx or dy)
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
        self.ambient_time += dt
        self.message_timer = max(0, self.message_timer - dt)
        for clip in self.caelen_clips.values():
            clip.update(dt * 1000)
        self.water_clip.update(dt * 1000)
        self.smoke_clip.update(dt * 1000)

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
                kind = self.world["legend"][char]
                asset_id = "terrain." + kind
                if asset_id in self.assets.manifest["assets"]:
                    self.assets.draw(self.canvas, asset_id, x * TILE - ox, y * TILE - oy)
                    if kind == "water" and (x + y) % 4 == 0:
                        self.assets.draw(self.canvas, self.water_clip.frame(), x * TILE - ox, y * TILE - oy)
                else:
                    draw_tile(self.canvas, self.tile_cache, kind, x * TILE - ox, y * TILE - oy, x, y)
        for obj in self.world["objects"]:
            draw_object(self.canvas, obj, ox, oy)
        if self.world["id"] == "eldenmere":
            mill = next((o for o in self.world["objects"] if o["id"] == "mill"), None)
            if mill:
                self.assets.draw(self.canvas, self.smoke_clip.frame(),
                                 (mill["x"] + 2) * TILE - ox, (mill["y"] - 1) * TILE - oy)

        # Temporary bridge: 16px-world graphics become 32px, while the new
        # Caelen PNG stays at native 32x48. Map coordinates/collision stay
        # unchanged; all new production maps/assets target the doubled scale.
        if self.world["id"] == "sanctuary_room":
            self.world_canvas.fill("#242d31")
            draw_sanctuary_room(self.world_canvas, self.world, self.assets,
                                ox, oy, self.ambient_time)
        else:
            pygame.transform.scale(self.canvas, (LOGICAL_W, LOGICAL_H), self.world_canvas)
        direction = ("right" if self.facing[0] > .3 else
                     "left" if self.facing[0] < -.3 else
                     "up" if self.facing[1] < 0 else "down")
        clip = self.caelen_clips["caelen." + ("walk_" if self.walking else "idle_") + direction]
        queue = RenderQueue()
        for npc in self.world.get("npcs", []):
            queue.add("entities", (npc["y"] + .9) * TILE,
                      lambda n=npc: self.draw_npc(n, ox, oy))
        queue.add("entities", self.y,
                  lambda: self.assets.draw(self.world_canvas, clip.frame(),
                                           (self.x - ox) * ART_SCALE,
                                           (self.y - oy) * ART_SCALE))
        queue.flush()
        self.present()
        self.dialogue.draw(self.window)
        pygame.display.flip()

    def draw_npc(self, npc, ox, oy):
        # Temporary NPC art uses the same 32x48 display size as Caelen.
        key = npc["color"]
        if key not in self.npc_sprites:
            sprite = pygame.Surface((16, 24), pygame.SRCALPHA)
            avatar(sprite, 8, 23, key)
            self.npc_sprites[key] = pygame.transform.scale(sprite, (32, 48))
        self.world_canvas.blit(self.npc_sprites[key],
                              (round(((npc["x"] + .5) * TILE - ox) * ART_SCALE - 16),
                               round(((npc["y"] + .9) * TILE - oy) * ART_SCALE - 47)))

    def present(self):
        screen_w, screen_h = self.window.get_size()
        scale = min(screen_w // LOGICAL_W, screen_h // LOGICAL_H)
        self.window.fill("#10151d")
        if scale >= 1:
            size = (LOGICAL_W * scale, LOGICAL_H * scale)
        else:
            # Small displays require a fitted fallback, without cropping.
            factor = min(screen_w / LOGICAL_W, screen_h / LOGICAL_H)
            size = (max(1, int(LOGICAL_W * factor)), max(1, int(LOGICAL_H * factor)))
        rendered = pygame.transform.scale(self.world_canvas, size)
        self.window.blit(rendered, ((screen_w - size[0]) // 2, (screen_h - size[1]) // 2))

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        flags = pygame.FULLSCREEN if self.fullscreen else pygame.RESIZABLE
        size = (0, 0) if self.fullscreen else self.windowed_size
        self.window = pygame.display.set_mode(size, flags)

    def run(self):
        running = True
        while running:
            dt = min(self.clock.tick(60) / 1000, 1 / 20)
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    running = False
                elif event.type == pygame.KEYDOWN and event.key in (pygame.K_F11, pygame.K_f):
                    self.toggle_fullscreen()
                elif event.type == pygame.VIDEORESIZE and not self.fullscreen:
                    self.windowed_size = event.size
                elif event.type == pygame.KEYDOWN and event.key in (pygame.K_e, pygame.K_SPACE):
                    if not self.dialogue.advance(self.window.get_size()):
                        self.interact()
            self.tick(dt)
            self.render()
        pygame.quit()


if __name__ == "__main__":
    Game().run()
