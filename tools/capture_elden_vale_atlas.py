"""Capture the production illustrated atlas, minimap and button-free world HUD.

Static views use Game.draw at actual display resolution. Navigation clips use
real input events; the minimap clip follows ordinary Game.update movement.
Final input hashes are checked after every artifact has been captured.
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

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame
from PIL import Image, ImageDraw, ImageFont

from main import Game
from regional_cartography import get_cartography

OUT = ROOT/'docs/reviews/elden_vale_atlas'
REGION = ROOT/'assets/maps/overworld/elden_vale/region.json'


def stamp():
    return datetime.now(timezone.utc).isoformat()


def sample_cache(game):
    service = getattr(game, '_regional_cartography', None)
    if service is None:
        return
    stats = service.cache_stats
    assert stats['tile_bytes'] <= stats['tile_budget']
    assert stats['icon_bytes'] <= stats['icon_budget']
    peak = getattr(game, '_capture_cartography_peak', {})
    for name in ('tile_bytes', 'tile_count', 'icon_bytes', 'icon_count', 'tile_loads'):
        peak[name] = max(peak.get(name, 0), stats[name])
    game._capture_cartography_peak = peak


def frame(game):
    game.draw()
    sample_cache(game)
    return Image.frombytes('RGB', game.window.get_size(), pygame.image.tobytes(game.window, 'RGB'))


def window_point(game, logical):
    scale, _, origin = game._ensure_ui_surface()
    return tuple(round(origin[axis]+logical[axis]*scale) for axis in (0, 1))


def event(game, kind, **values):
    pygame.event.post(pygame.event.Event(kind, **values))
    assert game.handle_events(), 'Capture input unexpectedly closed the game'


def key(game, code):
    event(game, pygame.KEYDOWN, key=code, repeat=False)


def visible_actor(world, actor, point):
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
        other = image.get_rect(topleft=(round(prop['position'][0])-foot[0], round(prop['position'][1])-foot[1]))
        if other.colliderect(rect) and pygame.mask.from_surface(image).overlap_area(mask, (rect.x-other.x, rect.y-other.y)) > 20:
            return False
    return True


def clear_landing(world, tile, actor=None):
    desired = pygame.Vector2(tile)*24
    for radius in range(0, 145, 4):
        offsets = [(0, 0)] if radius == 0 else [(0, radius), (-radius, 0), (radius, 0), (0, -radius)]
        for offset in offsets:
            point = desired+offset
            if (world.can_stand(point) and not world.town_entry_rect.colliderect(world.probe_rect(point))
                    and (actor is None or visible_actor(world, actor, point))):
                return point
    raise AssertionError(('No safe regional capture landing', tile))


def region_view(game, tile=(12, -25), facing='front', focus=None):
    game.map_open = False
    game.world = game.overworld_world
    game.player.facing = facing
    game.player.position.update(clear_landing(game.world, tile, game.player))
    game.player.moving = game.player.running = False
    game.player.walk_ms = 0
    game.location_seconds = game.opening_fade = game.transfer_cooldown = 0
    game.quest_ui.current_notice = None
    game.quest_ui.notices.clear()
    game.camera.reset()
    if focus is not None:
        game.camera.focus(tuple(value*24 for value in focus), duration=0)
    game.overworld_travel.update()
    assert game.world.is_overworld
    return {'requested_tile': list(tile), 'player_pixel': list(game.player.position),
            'camera_pixel': list(game.camera.position()), 'facing': facing}


def open_atlas(game):
    if not game.map_open:
        key(game, pygame.K_m)
    assert game.map_open
    ui = game.map_ui._regional()
    assert hasattr(ui, 'select_landmark'), 'Illustrated atlas UI is not ready'
    return ui


def save_view(game, name, report, extra=None):
    frame(game).save(OUT/name)
    record = {'window_size': list(game.window.get_size()), 'player_pixel': list(game.player.position),
              'text_scale': game.audio.text_scale, 'map_open': game.map_open,
              'minimap_visible': bool(game.minimap.visible)}
    if game.map_open:
        ui = game.map_ui._regional()
        record.update(center_tiles=list(ui.center), zoom=ui.zoom,
                      details_visible=bool(ui.details_visible),
                      selected=(ui.selected_landmark or {}).get('id'),
                      map_rect=list(ui.map_rect),
                      detail_panel=list(ui.detail_panel),
                      detail_scroll=ui.detail_scroll,
                      detail_max_scroll=ui.detail_max_scroll)
    if game.minimap.visible:
        record.update(minimap_rect=list(game.minimap.rect),
                      minimap_center_tiles=list(game.minimap.center_tiles))
    if extra:
        record.update(extra)
    report['views'][name] = record
    print(f'Captured {name}', flush=True)


def assert_component_independence(game):
    """Drawing either chart must not request a gameplay chunk or overview."""
    world = game.world
    original_draw, original_chunk = world.draw, world._render_chunk
    calls = []
    def forbidden(*args, **kwargs):
        calls.append(True)
        raise AssertionError('Cartography attempted to render gameplay terrain')
    world.draw = world._render_chunk = forbidden
    try:
        layer = pygame.Surface(game.ui_surface.get_size())
        if game.map_open:
            game.map_ui.draw(layer)
        else:
            game.minimap.draw(layer)
    finally:
        world.draw, world._render_chunk = original_draw, original_chunk
    sample_cache(game)
    return {'gameplay_terrain_requests': len(calls)}


def stills(game, report, early=False):
    region_view(game)
    save_view(game, 'minimap_town.png', report)
    assert game.minimap.visible
    report['minimap_component'] = assert_component_independence(game)
    ui = open_atlas(game)
    ui.fit()
    save_view(game, 'atlas_fit.png', report)
    report['atlas_component'] = assert_component_independence(game)
    ui.zoom_at(ui.map_rect.center, 3)
    ui.center.update(12, -28)
    save_view(game, 'atlas_close.png', report)
    ui.fit()
    game.audio.set_text_scale(1.5)
    ui.select_landmark('north_checkpoint')
    save_view(game, 'atlas_large_text.png', report)
    if not early:
        ui.fit()
        ui.select_landmark('western_stone_bridge')
        save_view(game, 'atlas_bridge_large_text.png', report)
        original = tuple(game.player.position)
        game.player.position.update(game.world._tile_point(game.world.region['town']['tile_position']))
        ui.select_landmark('eldenmere')
        save_view(game, 'atlas_overlap_large_text.png', report)
        game.player.position.update(original)
        event(game, pygame.VIDEORESIZE, w=480, h=320)
        ui.fit()
        ui.select_landmark('western_stone_bridge')
        save_view(game, 'atlas_small_large_text.png', report)
        assert ui.detail_max_scroll > 0
        key(game, pygame.K_END)
        assert ui.detail_scroll == ui.detail_max_scroll
        save_view(game, 'atlas_small_large_text_scrolled.png', report)
        key(game, pygame.K_HOME)
        assert ui.detail_scroll == 0
        ui.zoom = 1.25
        ui.center.update(-60, 0)
        ui.select_landmark('western_stone_bridge')
        save_view(game, 'atlas_small_edge_bridge.png', report)
        marker = ui.tile_to_map(ui.selected_landmark['tile_position'])
        marker_clearance = pygame.Rect(marker[0]-14, marker[1]-14, 28, 28)
        assert not ui.detail_panel.colliderect(marker_clearance), 'Card obscures selected bridge'
        before_center, before_zoom = tuple(ui.center), ui.zoom
        event(game, pygame.MOUSEBUTTONDOWN, button=5, pos=window_point(game, ui.detail_rect.center))
        assert ui.detail_scroll > 0, 'Legacy wheel must scroll the landmark card'
        assert tuple(ui.center) == before_center and ui.zoom == before_zoom
        event(game, pygame.MOUSEBUTTONDOWN, button=4, pos=window_point(game, ui.detail_rect.center))
        assert ui.detail_scroll == 0
        assert tuple(ui.center) == before_center and ui.zoom == before_zoom
        report['native_edge_card'] = {'selected_marker_clear': True,
                                     'legacy_wheel_scrolls_card': True,
                                     'geography_unchanged_during_card_scroll': True}
        event(game, pygame.VIDEORESIZE, w=960, h=640)
    game.audio.set_text_scale(1.0)
    if early:
        return

    ui.fit()
    ui.select_landmark('western_stone_bridge')
    save_view(game, 'atlas_bridge.png', report)
    ui.fit()
    ui.select_landmark('north_checkpoint')
    save_view(game, 'atlas_checkpoint.png', report)
    ui.fit()
    # Selection and the live player deliberately occupy the same atlas point.
    # Draw only while mapped; no gameplay update/portal can run at this position.
    original = tuple(game.player.position)
    game.player.position.update(game.world._tile_point(game.world.region['town']['tile_position']))
    ui.select_landmark('eldenmere')
    save_view(game, 'atlas_player_overlap.png', report)
    game.player.position.update(original)

    event(game, pygame.VIDEORESIZE, w=1440, h=810)
    ui.fit()
    ui.select_landmark('south_checkpoint')
    save_view(game, 'atlas_letterboxed.png', report)
    # Exercise a genuine letterboxed pointer anchor before returning to normal.
    before = tuple(ui.map_to_tile(ui.map_rect.center))
    event(game, pygame.MOUSEWHEEL, y=1, precise_y=1.0,
          pos=window_point(game, ui.map_rect.center), x=0)
    after = tuple(ui.map_to_tile(ui.map_rect.center))
    assert pygame.Vector2(before).distance_to(after) < .01
    event(game, pygame.VIDEORESIZE, w=960, h=640)
    key(game, pygame.K_ESCAPE)
    assert not game.map_open

    for name, tile, facing, focus in (
        ('minimap_forest.png', (-48, -68), 'back', None),
        ('minimap_bridge.png', (-98, 28), 'left', (-107, 29)),
        ('minimap_checkpoint.png', (20, -91), 'back', (20, -94)),
    ):
        extra = region_view(game, tile, facing, focus)
        save_view(game, name, report, extra)
        assert game.minimap.visible

    game.audio.set_text_scale(1.5)
    guard = pygame.Vector2(game.overworld_world.gates[0]['guard_position'])/24
    region_view(game, guard+pygame.Vector2(0, 1), 'back', (20, -94))
    save_view(game, 'minimap_large_text.png', report,
              {'interaction_hint': game.overworld_travel.interaction_hint()})
    assert game.minimap.visible
    game.audio.set_text_scale(1.0)

    # The removed Menu button is absent in the village and the bedroom too.
    game.world = game.town
    game.player.position.update(game.town.data['spawn'])
    game.player.facing = 'front'
    game.location_seconds = 0
    game.camera.reset()
    save_view(game, 'town_no_menu.png', report)
    assert not game.minimap.visible and not hasattr(game, '_hud_menu_rect')
    room_path = ROOT/game.town.data['interior_scenes']['sanctuary_bedroom']
    game.world = game._load_scene(room_path)
    game.player.position.update(game.world.data['spawn'])
    game.camera.reset()
    save_view(game, 'interior_no_menu.png', report)
    assert not game.minimap.visible and not hasattr(game, 'menu_rect')
    key(game, pygame.K_ESCAPE)
    assert game.pause.is_open, 'Escape must still open the pause menu'
    key(game, pygame.K_ESCAPE)
    assert not game.pause.is_open
    report['menu_button_removed'] = True
    report['escape_pause_preserved'] = True


def save_gif(name, images, durations, native=False):
    if native:
        images = [im.resize((480, 320), Image.Resampling.NEAREST) for im in images]
    samples = images[::max(1, len(images)//12)]
    palette_source = Image.new('RGB', (192*len(samples), 128))
    for index, sample in enumerate(samples):
        palette_source.paste(sample.resize((192, 128), Image.Resampling.NEAREST), (192*index, 0))
    palette = palette_source.quantize(colors=256, dither=Image.Dither.NONE)
    indexed = [im.quantize(palette=palette, dither=Image.Dither.NONE) for im in images]
    indexed[0].save(OUT/name, save_all=True, append_images=indexed[1:],
                    duration=durations, optimize=True, loop=0, disposal=1)
    print(f'Captured {name}', flush=True)


def navigation_clip(game):
    region_view(game)
    ui = open_atlas(game)
    ui.fit()
    images, durations = [frame(game)], [900]
    for _ in range(5):
        event(game, pygame.MOUSEWHEEL, y=1, precise_y=1.0, x=0,
              pos=window_point(game, ui.map_rect.center))
        images.append(frame(game));durations.append(220)
    start = pygame.Vector2(ui.map_rect.center)
    event(game, pygame.MOUSEBUTTONDOWN, button=1, pos=window_point(game, start))
    for step in range(1, 13):
        point = start+pygame.Vector2(step*4, step*1.5)
        event(game, pygame.MOUSEMOTION, pos=window_point(game, point), rel=(8, 3), buttons=(1, 0, 0))
        images.append(frame(game));durations.append(100)
    event(game, pygame.MOUSEBUTTONUP, button=1, pos=window_point(game, point))
    for code in (pygame.K_RIGHT, pygame.K_RIGHT, pygame.K_LEFT):
        key(game, code)
        images.append(frame(game));durations.append(400)
    key(game, pygame.K_f)
    images.append(frame(game));durations.append(1000)
    save_gif('atlas_navigation.gif', images, durations)
    key(game, pygame.K_m)
    assert not game.map_open
    return {'wheel_steps': 5, 'drag_events': 12, 'keyboard_selection': True,
            'fit_key': True, 'input': 'production Game.handle_events'}


def minimap_clip(game):
    world = game.overworld_world
    road = next(r for r in world.region['roads'] if r['id'] == 'western_farm_spur')
    region_view(game, road['points'][0])
    points = [pygame.Vector2(point)*24 for point in road['points']]
    images, durations = [frame(game)], [600]
    start = tuple(game.player.position)
    minimap_centers = [list(game.minimap.center_tiles)]
    target = 1
    for index in range(180):
        while target < len(points)-1 and game.player.position.distance_to(points[target]) < 4:
            target += 1
        direction = points[target]-game.player.position
        if target == len(points)-1 and direction.length() < 3:
            direction.update(0, 0)
        game.update(1/30, direction, False)
        if index % 3 == 0:
            images.append(frame(game));durations.append(100)
            minimap_centers.append(list(game.minimap.center_tiles))
            assert pygame.Vector2(game.minimap.center_tiles).distance_to(game.player.position/24) < .01
    images.append(frame(game));durations.append(800)
    travelled = game.player.position.distance_to(start)
    assert travelled > 100 and game.minimap.visible
    save_gif('minimap_tracking.gif', images, durations, native=True)
    return {'road_id': road['id'], 'start_pixel': list(start),
            'end_pixel': list(game.player.position), 'displacement_pixels': round(travelled, 2),
            'minimap_centers': minimap_centers, 'update_frames': 180,
            'movement': 'production Game.update, walking'}


def before_after():
    old = Image.open(ROOT/'docs/reviews/elden_vale_polish/regional_map.png').convert('RGB')
    new = Image.open(OUT/'atlas_fit.png').convert('RGB')
    result = Image.new('RGB', (1920, 690), '#233e34')
    result.paste(old, (0, 50));result.paste(new, (960, 50))
    draw = ImageDraw.Draw(result)
    font = ImageFont.truetype(str(ROOT/'assets/ui/fonts/AtkinsonHyperlegible-Bold.ttf'), 22)
    draw.text((20, 12), 'BEFORE', fill='#eee0b4', font=font)
    draw.text((980, 12), 'ILLUSTRATED REGIONAL ATLAS', fill='#eee0b4', font=font)
    result.save(OUT/'before_after.png')


def inputs():
    names = ['main.py', 'map_ui.py', 'overworld_map.py', 'overworld_minimap.py',
             'regional_cartography.py', 'ui_style.py', 'tools/capture_elden_vale_atlas.py',
             REGION.relative_to(ROOT).as_posix()]
    paths = [ROOT/name for name in names]
    paths.extend(sorted((ROOT/'assets/cartography/elden_vale').rglob('*')))
    paths.extend(sorted((ROOT/'assets/ui/fonts').glob('*.ttf')))
    return {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths if path.is_file()}


def capture(early=False, stills_only=False):
    OUT.mkdir(parents=True, exist_ok=True)
    source_hashes = inputs()
    with tempfile.TemporaryDirectory(prefix='elden-vale-atlas-') as temporary:
        game = Game(window_size=(960, 640), fullscreen=False, start_on_title=False,
                    save_path=Path(temporary)/'journey.json', settings_path=Path(temporary)/'settings.json')
        try:
            pygame.event.clear()
            game.audio.set_music(0);game.audio.set_effects(0)
            game.opening_fade = game.transfer_cooldown = 0
            region_view(game)
            service = get_cartography(game)
            assert service.art_available and service.compatible, 'Illustrated cartographic art is not ready'
            assert hasattr(game, 'minimap'), 'Minimap integration is not ready'
            stage = 'early' if early else 'stills_review' if stills_only else 'final'
            report = {'actual_renderer': True, 'quest_progress_seeded': False,
                      'capture_stage': stage, 'started_at_utc': stamp(), 'views': {}}
            stills(game, report, early)
            if not early and not stills_only:
                report['navigation'] = navigation_clip(game)
                report['minimap_walk'] = minimap_clip(game)
            if not early:
                before_after()
            assert service is game._regional_cartography, 'Atlas and minimap should share a cartographic cache'
            report['cartography_cache'] = service.cache_stats
            report['peak_cartography_cache'] = getattr(game, '_capture_cartography_peak', {})
            for name, digest in source_hashes.items():
                assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == digest, f'Capture input changed: {name}'
            report['render_input_sha256'] = source_hashes
            report['finished_at_utc'] = stamp()
            report['captures'] = {}
            for path in sorted(OUT.iterdir()):
                if path.suffix.lower() not in ('.png', '.gif'):
                    continue
                with Image.open(path) as image:
                    report['captures'][path.name] = {'size': list(image.size),
                        'frames': getattr(image, 'n_frames', 1), 'bytes': path.stat().st_size}
            name = ('early_capture_report.json' if early else
                    'stills_capture_report.json' if stills_only else 'capture_report.json')
            (OUT/name).write_text(json.dumps(report, indent=2)+'\n')
            if not early and not stills_only:
                (OUT/'early_capture_report.json').unlink(missing_ok=True)
                (OUT/'stills_capture_report.json').unlink(missing_ok=True)
            print(json.dumps({'stage': report['capture_stage'], 'cache': report['cartography_cache'],
                              'views': list(report['views'])}, indent=2), flush=True)
        finally:
            pygame.quit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--early', action='store_true', help='Capture diagnostic Fit/zoom/minimap/text views only')
    group.add_argument('--stills-only', action='store_true', help='Capture all diagnostic still views without clips')
    args = parser.parse_args()
    capture(args.early, args.stills_only)
