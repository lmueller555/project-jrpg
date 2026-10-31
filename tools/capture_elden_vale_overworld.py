"""Capture Elden Vale through the production Game and sparse world renderer.

The full-bounds overview is assembled from 384px render requests reduced 1:8
as they arrive. Its largest world render surface is one chunk. No replacement
scenery is painted. Static views use the game camera and display UI; the GIF
uses ordinary player movement and automatic town contacts in both directions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame
from PIL import Image, ImageDraw, ImageFont

from main import Game
from overworld_travel import TOWN_RETURN, WORLD_ID
from overworld_world import CHUNK_PIXELS

OUT = ROOT / "docs/reviews/elden_vale_overworld"


def frame(game: Game) -> Image.Image:
    game.draw()
    return Image.frombytes("RGB", game.window.get_size(), pygame.image.tobytes(game.window, "RGB"))


def save_view(game: Game, name: str, tile_position, *, focus_tile=None, facing="front") -> None:
    game.world = game.overworld_world
    game.player.position.update(*(value * 24 for value in tile_position))
    game.player.facing = facing
    game.player.moving = game.player.running = False
    game.player.walk_ms = 0
    game.map_open = False
    game.location_seconds = 0
    game.location_label = None
    game.transfer_cooldown = 0
    game.camera.reset()
    if focus_tile is not None:
        game.camera.focus(tuple(value * 24 for value in focus_tile), duration=0)
    game.overworld_travel.update()
    assert game.world.data["id"] == WORLD_ID, name
    frame(game).save(OUT / name)
    print(f"Captured {name}", flush=True)


def gif_frame(game: Game, images: list, durations: list, duration=100) -> None:
    images.append(frame(game))
    durations.append(duration)


def save_gif(name: str, images: list[Image.Image], durations: list[int]) -> None:
    # GIF previews retain the game's 480x320 native pixel grid. One palette
    # across the clip and differential frame storage avoid large RGB frames.
    native = [image.resize((480, 320), Image.Resampling.NEAREST) for image in images]
    samples = native[::max(1, len(native) // 12)]
    palette_source = Image.new("RGB", (160 * len(samples), 235))
    for index, sample in enumerate(samples):
        palette_source.paste(sample.resize((160, 107), Image.Resampling.NEAREST), (160 * index, 0))
        # Give the small leader and HUD colors representation alongside large
        # areas of grass. Both normal tracking and the town's clamped camera
        # appear in these clips.
        palette_source.paste(sample.crop((208, 104, 272, 168)).resize((128, 128), Image.Resampling.NEAREST), (160 * index, 107))
        palette_source.paste(sample.crop((224, 228, 256, 276)).resize((32, 128), Image.Resampling.NEAREST), (160 * index + 128, 107))
    palette = palette_source.quantize(colors=256, dither=Image.Dither.NONE)
    indexed = [image.quantize(palette=palette, dither=Image.Dither.NONE) for image in native]
    indexed[0].save(OUT / name, save_all=True, append_images=indexed[1:],
                    duration=durations, loop=0, optimize=True, disposal=1)


def capture_transition(game: Game) -> list[list[str]]:
    images, durations, transitions = [], [], []
    game.map_open = False
    game.world = game.town
    game.player.position.update(TOWN_RETURN)
    game.player.facing = "front"
    game.opening_fade = game.transfer_cooldown = 0
    game.location_seconds = 0
    game.camera.reset()
    game.overworld_travel.restore()
    game.overworld_travel.update()
    gif_frame(game, images, durations, 600)

    def tick(direction=(0, 0)):
        before = game.world.data["id"]
        game.update(1 / 30, direction, False)
        after = game.world.data["id"]
        if before != after:
            transitions.append([before, after])
        return before != after

    def walk_to_transfer(direction, destination):
        for index in range(150):
            transferred = tick(direction)
            if index % 3 == 0 or transferred:
                gif_frame(game, images, durations, 100)
            if transferred:
                assert game.world.data["id"] == destination
                return
        raise AssertionError(("Town contact not reached", direction, tuple(game.player.position)))

    walk_to_transfer((0, 1), WORLD_ID)
    for index in range(30):
        tick()
        if index % 3 == 0:
            gif_frame(game, images, durations, 100)
    walk_to_transfer((0, -1), game.town.data["id"])
    for _ in range(15):
        tick()
    gif_frame(game, images, durations, 900)
    save_gif("town_transition.gif", images, durations)
    assert len(transitions) == 2, transitions
    print("Captured town_transition.gif: " + json.dumps(transitions), flush=True)
    return transitions


def capture_walk(game: Game) -> None:
    game.world = game.overworld_world
    game.player.position.update(8 * 24, -64 * 24)
    game.transfer_cooldown = game.opening_fade = 0
    game.location_seconds = 0
    game.camera.reset()
    images, durations = [], []
    gif_frame(game, images, durations, 500)
    for index in range(120):
        game.update(1 / 30, (12, -32), False)
        if index % 3 == 0:
            gif_frame(game, images, durations)
    gif_frame(game, images, durations, 600)
    save_gif("region_walk.gif", images, durations)
    print("Captured region_walk.gif", flush=True)


def capture_overview(game: Game) -> dict:
    world = game.overworld_world
    scale = 8
    bounds = world.bounds
    overview = pygame.Surface((bounds.width // scale, bounds.height // scale))
    chunk = pygame.Surface((CHUNK_PIXELS, CHUNK_PIXELS))
    reduced = pygame.Surface((CHUNK_PIXELS // scale, CHUNK_PIXELS // scale))
    hidden_player = SimpleNamespace(position=pygame.Vector2(), story_visible=False)
    count = (bounds.width // CHUNK_PIXELS) * (bounds.height // CHUNK_PIXELS)
    completed = 0
    max_render_bytes = 0
    max_metadata = 0
    for y in range(bounds.top, bounds.bottom, CHUNK_PIXELS):
        for x in range(bounds.left, bounds.right, CHUNK_PIXELS):
            world.draw(chunk, (x, y), hidden_player, 900, include_ui=False)
            pygame.transform.smoothscale(chunk, reduced.get_size(), reduced)
            overview.blit(reduced, ((x - bounds.left) // scale, (y - bounds.top) // scale))
            stats = world.cache_stats
            max_render_bytes = max(max_render_bytes, stats["render_bytes"])
            max_metadata = max(max_metadata, stats["metadata_chunks"])
            completed += 1
        if completed % 128 == 0 or completed == count:
            print(f"Overview: {completed}/{count} streamed chunks", flush=True)
    pygame.image.save(overview, OUT / "region_overview.png")
    annotated = Image.frombytes("RGB", overview.get_size(), pygame.image.tobytes(overview, "RGB"))
    draw = ImageDraw.Draw(annotated)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
    labels = [
        ("Eldenmere", world.region["town"]["tile_position"], (30, -8)),
        ("Western bridge — broken", world.region["bridge"]["tile_position"], (-205, 26)),
        ("Northern checkpoint", world.region["gates"][0]["tile_position"], (20, -28)),
        ("Southern checkpoint", world.region["gates"][1]["tile_position"], (20, 16)),
    ]
    for title, tile, offset in labels:
        point = ((tile[0] * 24 - bounds.left) / scale, (tile[1] * 24 - bounds.top) / scale)
        label = (round(point[0] + offset[0]), round(point[1] + offset[1]))
        text_box = draw.textbbox(label, title, font=font)
        draw.line((point, (label[0], label[1] + 8)), fill="#f2e1b5", width=2)
        draw.ellipse((point[0] - 3, point[1] - 3, point[0] + 3, point[1] + 3), fill="#eec775")
        draw.rectangle((text_box[0] - 5, text_box[1] - 4, text_box[2] + 5, text_box[3] + 4), fill="#243d33")
        draw.text(label, title, font=font, fill="#f2e1b5")
    draw.text((20, 18), "ELDEN VALE  /  actual renderer  /  complete authored bounds at 1:8", font=font, fill="#f2e1b5", stroke_width=2, stroke_fill="#243d33")
    annotated.save(OUT / "region_overview_annotated.png")
    report = {"streamed_chunks": completed, "largest_world_render_surface": [CHUNK_PIXELS, CHUNK_PIXELS],
              "overview_size": list(overview.get_size()), "max_render_cache_bytes": max_render_bytes,
              "max_metadata_chunks": max_metadata, "configured_render_budget": world._render_cache.limit}
    assert max_render_bytes <= world._render_cache.limit
    assert max_metadata <= world._metadata_cache.limit
    print("Captured overview: " + json.dumps(report), flush=True)
    return report


def capture(skip_overview=False, only_overview=False) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="elden-vale-capture-") as temporary:
        game = Game(window_size=(960, 640), fullscreen=False, start_on_title=False,
                    save_path=Path(temporary) / "journey.json",
                    settings_path=Path(temporary) / "settings.json")
        try:
            game.audio.set_music(0)
            game.audio.set_effects(0)
            game.opening_fade = game.transfer_cooldown = 0
            report = {"actual_renderer": True, "quest_progress_seeded": False}
            if not only_overview:
                save_view(game, "town_miniature.png", (12, -25), focus_tile=(12, -29))
                save_view(game, "western_bridge.png", (-101, 29), focus_tile=(-109, 29))
                save_view(game, "northern_checkpoint.png", (20, -91), focus_tile=(20, -94), facing="back")
                save_view(game, "southern_checkpoint.png", (28, 91), focus_tile=(28, 94))
                save_view(game, "eastern_foothills.png", (74, -20), focus_tile=(78, -24))
                save_view(game, "northern_woodland.png", (-48, -68), focus_tile=(-48, -70))
                save_view(game, "southern_farmland.png", (46, 75), focus_tile=(46, 71))
                game.world = game.overworld_world
                game.player.position.update(game.world.town_exit)
                game.camera.reset()
                game.map_ui.reset()
                game.map_open = True
                frame(game).save(OUT / "regional_map.png")
                game.map_open = False
                print("Captured regional_map.png", flush=True)
                report["transitions"] = capture_transition(game)
                capture_walk(game)
            if not skip_overview:
                report["overview"] = capture_overview(game)
            report["region_sha256"] = hashlib.sha256(game.overworld_world.path.read_bytes()).hexdigest()
            report["art_manifest_sha256"] = hashlib.sha256(
                (ROOT / "assets/terrain/overworld/elden_vale/art.json").read_bytes()).hexdigest()
            report["captures"] = {}
            for path in sorted(OUT.glob("*")):
                if path.suffix not in (".png", ".gif") or path.name == "atlas_reference.png":
                    continue
                with Image.open(path) as image:
                    report["captures"][path.name] = {
                        "size": list(image.size), "frames": getattr(image, "n_frames", 1),
                        "bytes": path.stat().st_size,
                    }
            payload = json.dumps(report, indent=2) + "\n"
            Path("/tmp/elden_vale_capture_report.json").write_text(payload)
            (OUT / "capture_report.json").write_text(payload)
            print(json.dumps(report, indent=2), flush=True)
        finally:
            pygame.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-overview", action="store_true")
    parser.add_argument("--only-overview", action="store_true")
    arguments = parser.parse_args()
    capture(arguments.skip_overview, arguments.only_overview)
