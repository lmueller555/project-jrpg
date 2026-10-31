"""Capture the Elden Vale place-composition pass through the production renderer.

The full-bounds overview is assembled from 384px render requests reduced 1:8
as they arrive. Its largest world render surface is one chunk. No replacement
scenery is painted. Static views use the game camera and display UI; the GIF
uses ordinary player movement and automatic town contacts in both directions.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
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

OUT = ROOT / "docs/reviews/elden_vale_composition"
BEFORE = ROOT / "docs/reviews/elden_vale_polish"


def frame(game: Game) -> Image.Image:
    game.draw()
    return Image.frombytes("RGB", game.window.get_size(), pygame.image.tobytes(game.window, "RGB"))


def clear_landing(world, tile_position, actor=None):
    desired = pygame.Vector2(tile_position) * 24
    for radius in range(0, 145, 4):
        offsets = [(0, 0)] if radius == 0 else [(0, radius), (-radius, 0), (radius, 0), (0, -radius)]
        for offset in offsets:
            point = desired + offset
            if (world.can_stand(point) and not world.town_entry_rect.colliderect(world.probe_rect(point))
                    and (actor is None or visible_actor(world, actor, point))):
                return point
    raise AssertionError(("No safe capture landing", tile_position))


def visible_actor(world, actor, point):
    """Choose a real clear pose so the review sprite is not hidden by a canopy."""
    surface = actor.sprite()
    anchor = world.data['player_draw_anchor']
    rect = surface.get_rect(topleft=(round(point.x)-anchor[0], round(point.y)-anchor[1]))
    mask = pygame.mask.from_surface(surface)
    for prop in world._static_props(rect):
        if prop['position'][1]+prop.get('sort_offset', 0) <= point.y+6:
            continue
        image, foot = world._prop_image(prop['key'])
        if image is None:
            continue
        other = image.get_rect(topleft=(round(prop['position'][0])-foot[0],
                                        round(prop['position'][1])-foot[1]))
        if other.colliderect(rect) and pygame.mask.from_surface(image).overlap_area(mask, (rect.x-other.x, rect.y-other.y)) > 20:
            return False
    return True


def save_view(game: Game, name: str, tile_position, *, focus_tile=None, facing="front") -> dict:
    game.world = game.overworld_world
    game.player.facing = facing
    game.player.moving = game.player.running = False
    game.player.walk_ms = 0
    game.player.position.update(clear_landing(game.world, tile_position, game.player))
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
    return {"requested_player_tile": list(tile_position),
            "actual_player_pixel": list(game.player.position),
            "focus_tile": list(focus_tile or tile_position),
            "camera_pixel": list(game.camera.position())}


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


def capture_walk(game: Game) -> dict:
    game.world = game.overworld_world
    roads = game.world.region['roads']
    road = next((road for road in roads if road.get('review_walk')), None)
    if road is None:
        road = next((road for road in roads if road.get('kind') == 'cart'), roads[0])
    points = [pygame.Vector2(point)*24 for point in road['points']]
    game.player.position.update(clear_landing(game.world, road['points'][0]))
    game.transfer_cooldown = game.opening_fade = 0
    game.location_seconds = 0
    game.camera.reset()
    start = tuple(game.player.position)
    images, durations = [], []
    gif_frame(game, images, durations, 500)
    target = 1
    for index in range(180):
        while target < len(points)-1 and game.player.position.distance_to(points[target]) < 4:
            target += 1
        direction = points[target]-game.player.position
        if target == len(points)-1 and direction.length() < 3:
            direction.update(0, 0)
        game.update(1 / 30, direction, False)
        if index % 3 == 0:
            gif_frame(game, images, durations)
    gif_frame(game, images, durations, 600)
    save_gif("place_walk.gif", images, durations)
    travelled = game.player.position.distance_to(start)
    assert travelled > 100, ('Capture walk is blocked', road['id'], travelled)
    assert game.world.data['id'] == WORLD_ID
    print(f"Captured place_walk.gif along {road['id']}: {travelled:.1f}px displacement", flush=True)
    return {'road_id': road['id'], 'start_pixel': list(start),
            'end_pixel': list(game.player.position), 'displacement_pixels': round(travelled, 2),
            'update_frames': 180, 'movement': 'production Game.update, walking'}


def capture_bridge_width(game: Game, view: dict) -> dict:
    """Put a measured three-tile guide on the actual rendered abutments.

    The review overlay never alters the runtime image or its collision. The
    clearance comes from the native art record and must match the world's
    future repaired deck; the broken gap is independently checked by alpha.
    """
    world = game.overworld_world
    bridge = world.region['bridge']
    key = bridge.get('broken_art_key', 'broken_bridge')
    record = world._art['props'][key]
    sprite, anchor = world._prop_image(key)
    top = record['deck_top_px']
    bottom = record['deck_bottom_px']
    clear = record.get('deck_clear_width_px', bottom-top)
    assert bottom-top == clear == 72, ('Bridge roadway is not three native tiles', record)
    assert sprite.get_width() == 288, ('River span changed', sprite.get_size())
    deck = world._tile_rect(bridge['deck_rect_tiles'])
    assert deck.height == 72, ('Physical repaired deck must also be three tiles', deck)
    position = world._tile_point(bridge['tile_position'])
    sprite_origin = (position[0]-anchor[0], position[1]-anchor[1])
    world_top = sprite_origin[1]+top
    world_bottom = sprite_origin[1]+bottom
    assert abs(world_top-deck.top) <= 1 and abs(world_bottom-deck.bottom) <= 1, (
        'Artwork and physical deck do not align', world_top, world_bottom, deck)

    with Image.open(ROOT/record['image']) as source:
        alpha = source.convert('RGBA').getchannel('A')
        mid = source.width//2
        assert alpha.crop((mid, 0, mid+1, source.height)).getbbox() is None, 'Broken gap has visible crossing pixels'
        left = right = mid
        while left > 0 and alpha.crop((left-1, 0, left, source.height)).getbbox() is None:
            left -= 1
        while right < source.width and alpha.crop((right, 0, right+1, source.height)).getbbox() is None:
            right += 1
        assert right-left >= 48, ('Broken gap is not visibly clear', left, right)

    with Image.open(OUT/'western_bridge.png') as source:
        image = source.convert('RGBA')
    overlay = Image.new('RGBA', image.size)
    draw = ImageDraw.Draw(overlay)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 17)
    camera = view['camera_pixel']
    scale = image.width/480
    for sample_x in record.get('deck_sample_x_px', [40, 248]):
        x = (sprite_origin[0]+sample_x-camera[0])*scale
        y = (world_top-camera[1])*scale
        # Three 24px world-grid cells measure only the roadway between rails.
        for index in range(3):
            box = (round(x-12*scale), round(y+index*24*scale),
                   round(x+12*scale), round(y+(index+1)*24*scale))
            draw.rectangle(box, fill=(74, 190, 210, 45), outline=(242, 225, 176, 235), width=2)
            draw.text((box[0]+4, box[1]+3), str(index+1), font=font,
                      fill=(255, 247, 218, 255), stroke_width=1, stroke_fill=(23, 46, 44, 255))
    title = 'CLEAR ROADWAY: 3 x 24 px = 72 native pixels'
    draw.rectangle((12, 12, 620, 45), fill=(24, 45, 39, 235))
    draw.text((22, 19), title, font=font, fill=(249, 236, 201, 255))
    image.alpha_composite(overlay)
    image.convert('RGB').save(OUT/'bridge_width_audit.png')
    print('Captured bridge_width_audit.png: clear roadway 72px; transparent broken gap '+str(right-left)+'px', flush=True)
    return {'art_key': key, 'native_sprite_size': list(sprite.get_size()),
            'deck_top_px': top, 'deck_bottom_px': bottom, 'clear_roadway_pixels': clear,
            'clear_roadway_tiles': clear/24, 'art_world_top': world_top,
            'art_world_bottom': world_bottom, 'repaired_deck_rect_pixels': list(deck),
            'transparent_gap_columns': [left, right], 'transparent_gap_width_px': right-left,
            'audit_uses': 'Production western_bridge.png plus review-only measured grid overlay'}


def capture_comparisons(game: Game):
    """Render the new region at the previous review's exact camera origins."""
    pairs = [('farmstead_west.png', 'Western farmstead'),
             ('orchard.png', 'Village orchard'),
             ('northern_woodland.png', 'Northern woodland'),
             ('western_bridge.png', 'Western bridge — same camera position'),
             ('eastern_foothills.png', 'Eastern foothills')]
    panel = Image.new('RGB', (960, len(pairs)*352+44), '#243d33')
    draw = ImageDraw.Draw(panel)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 16)
    draw.text((16, 12), 'BEFORE', fill='#f2e1b5', font=font)
    draw.text((496, 12), 'COMPOSITION PASS — same camera coordinates', fill='#f2e1b5', font=font)
    previous = json.loads((BEFORE/'capture_report.json').read_text())
    actual = {}
    for index, (filename, title) in enumerate(pairs):
        top = 44+index*352
        with Image.open(BEFORE/filename) as image:
            panel.paste(image.convert('RGB').resize((480,320), Image.Resampling.NEAREST), (0, top+24))
        prior = previous['views'][filename]
        camera = prior['camera_pixel']
        game.world = game.overworld_world
        desired = pygame.Vector2(prior['actual_player_pixel'])/24
        game.player.position.update(clear_landing(game.world, desired, game.player))
        game.player.moving = game.player.running = False
        game.player.facing = 'left' if filename == 'western_bridge.png' else 'front'
        game.player.walk_ms = 0
        game.map_open = False
        game.camera.reset()
        game.camera.focus((camera[0]+240, camera[1]+160), duration=0)
        actual_camera = tuple(game.camera.position())
        assert all(abs(a-b) < 1 for a,b in zip(actual_camera,camera)), ('Comparison camera drift', filename, camera, actual_camera)
        current = frame(game)
        panel.paste(current.resize((480,320), Image.Resampling.NEAREST), (480, top+24))
        actual[filename] = {'prior_camera_pixel': camera, 'new_camera_pixel': list(actual_camera),
                            'new_player_pixel': list(game.player.position)}
        draw.text((16, top+2), title, fill='#f2e1b5', font=font)
    panel.save(OUT/'before_after.png')
    print('Captured before_after.png', flush=True)
    return actual


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
    labels.extend((record.get('name', record['id']), record['tile_position'], (20, 8))
                  for record in world.region.get('setpieces', [])
                  if record.get('kind') in ('farmstead', 'farm', 'orchard'))
    for title, tile, offset in labels:
        point = ((tile[0] * 24 - bounds.left) / scale, (tile[1] * 24 - bounds.top) / scale)
        label = (round(point[0] + offset[0]), round(point[1] + offset[1]))
        text_box = draw.textbbox(label, title, font=font)
        draw.line((point, (label[0], label[1] + 8)), fill="#f2e1b5", width=2)
        draw.ellipse((point[0] - 3, point[1] - 3, point[0] + 3, point[1] + 3), fill="#eec775")
        draw.rectangle((text_box[0] - 5, text_box[1] - 4, text_box[2] + 5, text_box[3] + 4), fill="#243d33")
        draw.text(label, title, font=font, fill="#f2e1b5")
    draw.text((20, 18), "ELDEN VALE  /  place composition  /  actual renderer at 1:8", font=font, fill="#f2e1b5", stroke_width=2, stroke_fill="#243d33")
    annotated.save(OUT / "region_overview_annotated.png")
    report = {"streamed_chunks": completed, "largest_world_render_surface": [CHUNK_PIXELS, CHUNK_PIXELS],
              "overview_size": list(overview.get_size()), "max_render_cache_bytes": max_render_bytes,
              "max_metadata_chunks": max_metadata, "configured_render_budget": world._render_cache.limit}
    assert max_render_bytes <= world._render_cache.limit
    assert max_metadata <= world._metadata_cache.limit
    print("Captured overview: " + json.dumps(report), flush=True)
    return report


def setpiece_views(game):
    records = game.overworld_world.region.get('setpieces', [])
    farms = sorted((record for record in records if record.get('kind') in ('farm', 'farmstead')),
                   key=lambda record: record['tile_position'][0])
    views = []
    for label, record in zip(('west', 'south', 'east'), farms):
        review = record.get('review', {})
        center = record['tile_position']
        views.append((f'farmstead_{label}.png', review.get('player_tile', record.get('approach_tile', center)),
                      review.get('focus_tile', center), review.get('facing', 'back')))
    for record in records:
        kind = record.get('kind', '')
        filename = {'orchard': 'orchard.png', 'riverbank': 'riverbank.png'}.get(kind)
        if filename is None:
            continue
        review = record.get('review', {})
        center = record['tile_position']
        views.append((filename, review.get('player_tile', record.get('approach_tile', center)),
                      review.get('focus_tile', center), review.get('facing', 'front')))
    return views


def scene_view(game, filename, identifier, fallback_player, fallback_focus, facing='front'):
    record = next((scene for scene in game.overworld_world.region.get('setpieces', [])
                   if scene['id'] == identifier), None)
    review = (record or {}).get('review', {})
    return (filename, review.get('player_tile', (record or {}).get('approach_tile', fallback_player)),
            review.get('focus_tile', (record or {}).get('tile_position', fallback_focus)),
            review.get('facing', facing))


def capture(skip_overview=False, only_overview=False, early=False, stills_only=False) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="elden-vale-composition-capture-") as temporary:
        game = Game(window_size=(960, 640), fullscreen=False, start_on_title=False,
                    save_path=Path(temporary) / "journey.json",
                    settings_path=Path(temporary) / "settings.json")
        try:
            game.audio.set_music(0)
            game.audio.set_effects(0)
            game.opening_fade = game.transfer_cooldown = 0
            world = game.overworld_world
            assert world.region.get('detail_art_manifest'), 'Detailed region layout is not ready'
            assert (ROOT/world.region['detail_art_manifest']).exists(), 'Detailed region art is not ready'
            assert 'farm_house' in world._art.get('props', {}), 'Detailed art is not loaded by the renderer'
            input_paths = {world.path, ROOT/'overworld_world.py', ROOT/'overworld_environment.py',
                           ROOT/world.region['art_manifest'], ROOT/world.region['detail_art_manifest'], Path(__file__).resolve()}
            if world.region.get('composition_art_manifest'):
                input_paths.add(ROOT/world.region['composition_art_manifest'])
            input_paths.update(ROOT/record['image'] for group in ('tiles', 'props')
                               for record in world._art.get(group, {}).values())
            input_hashes = {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                            for path in sorted(input_paths)}
            report = {"actual_renderer": True, "quest_progress_seeded": False,
                      'capture_stage': ('early_composition' if early else
                                        'stills_review' if stills_only else
                                        'overview_review' if only_overview else
                                        'partial_review' if skip_overview else 'final'),
                      'started_at_utc': datetime.now(timezone.utc).isoformat(), 'views': {}}
            if report['capture_stage'] == 'final':
                assert world.region.get('bridge', {}).get('broken_art_key') == 'broken_bridge_wide', 'Wide bridge layout is not ready'
                assert 'broken_bridge_wide' in world._art.get('props', {}), 'Wide bridge artwork is not ready'
            if not only_overview:
                views = [('town_miniature.png', (12, -25), (12, -29), 'front'),
                         ('village_outskirts.png', (3, -11), (3, -13), 'back'),
                         ('western_bridge.png', (-101, 29), (-109, 29), 'left'),
                         scene_view(game, 'northern_checkpoint.png', 'north_checkpoint_life',
                                    (20, -91), (20, -94), 'back'),
                         scene_view(game, 'southern_checkpoint.png', 'south_checkpoint_life',
                                    (28, 91), (28, 94), 'front'),
                         scene_view(game, 'eastern_foothills.png', 'foothill_overlook',
                                    (74, -20), (78, -24)),
                         scene_view(game, 'northern_woodland.png', 'woodland_clearing',
                                    (-48, -68), (-48, -70)),
                         ('forest_interior.png', (-80, -66), (-80, -69), 'front'),
                         ('southern_farmland.png', (46, 75), (46, 71), 'front'),
                         scene_view(game, 'relief_staging.png', 'relief_staging',
                                    (-68, 19), (-68, 16), 'back')]
                views.extend(setpiece_views(game))
                if not any(view[0] == 'riverbank.png' for view in views):
                    views.append(('riverbank.png', (108, -27), (113, -27), 'right'))
                    views.append(('riverbank_stony.png', (107, 37), (113, 35), 'right'))
                if early:
                    views = [view for view in views if view[0] in (
                        'farmstead_west.png', 'farmstead_south.png', 'farmstead_east.png',
                        'orchard.png', 'relief_staging.png', 'northern_checkpoint.png',
                        'southern_checkpoint.png', 'northern_woodland.png', 'forest_interior.png')]
                for filename, player, focus, facing in views:
                    report['views'][filename] = save_view(game, filename, player, focus_tile=focus, facing=facing)
                if early:
                    path = OUT/'early_capture_report.json'
                    path.write_text(json.dumps(report, indent=2)+'\n')
                    print('Early composition views ready', flush=True)
                    return
                if world.region.get('bridge', {}).get('broken_art_key') in world._art.get('props', {}):
                    report['bridge_width'] = capture_bridge_width(game, report['views']['western_bridge.png'])
                if not stills_only:
                    report["transitions"] = capture_transition(game)
                    report['walk'] = capture_walk(game)
                report['comparison_views'] = capture_comparisons(game)
            if not skip_overview and not stills_only:
                report["overview"] = capture_overview(game)
            if report['capture_stage'] == 'final':
                for diagnostic in ('early_capture_report.json', 'stills_review_capture_report.json',
                                   'overview_review_capture_report.json', 'partial_review_capture_report.json'):
                    (OUT/diagnostic).unlink(missing_ok=True)
            report["region_sha256"] = hashlib.sha256(game.overworld_world.path.read_bytes()).hexdigest()
            report["art_manifest_sha256"] = hashlib.sha256(
                (ROOT / "assets/terrain/overworld/elden_vale/art.json").read_bytes()).hexdigest()
            report['detail_art_manifest_sha256'] = hashlib.sha256(
                (ROOT / game.overworld_world.region['detail_art_manifest']).read_bytes()).hexdigest()
            if game.overworld_world.region.get('composition_art_manifest'):
                report['composition_art_manifest_sha256'] = hashlib.sha256(
                    (ROOT / game.overworld_world.region['composition_art_manifest']).read_bytes()).hexdigest()
            report['engine_sha256'] = hashlib.sha256((ROOT/'overworld_world.py').read_bytes()).hexdigest()
            helper = ROOT/'overworld_environment.py'
            if helper.exists():
                report['environment_helper_sha256'] = hashlib.sha256(helper.read_bytes()).hexdigest()
            for path, digest in input_hashes.items():
                assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == digest, ('Render input changed; rerun capture', path)
            report['render_input_sha256'] = input_hashes
            report['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
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
            Path("/tmp/elden_vale_composition_capture_report.json").write_text(payload)
            report_name = 'capture_report.json' if report['capture_stage'] == 'final' else report['capture_stage']+'_capture_report.json'
            (OUT / report_name).write_text(payload)
            print(json.dumps(report, indent=2), flush=True)
        finally:
            pygame.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-overview", action="store_true")
    parser.add_argument("--only-overview", action="store_true")
    parser.add_argument('--early', action='store_true', help='Capture representative farms, orchard, relief and checkpoint compositions')
    parser.add_argument('--stills-only', action='store_true', help='Skip animated previews')
    arguments = parser.parse_args()
    capture(arguments.skip_overview, arguments.only_overview, arguments.early, arguments.stills_only)
