"""Capture actual Elden Vale HD gameplay with disposable saves and native buffers.

Fixed view fixtures position the player on reachable open ground; all subsequent
movement and reciprocal contacts use Game.update. No replacement scenery is drawn.
"""
from __future__ import annotations

import argparse
import copy
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import sys
import tempfile
from time import perf_counter
from types import SimpleNamespace

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame
from PIL import Image, ImageChops, ImageDraw

from main import Game
from overworld_travel import TOWN_RETURN, WORLD_ID
from overworld_world import CHUNK_PIXELS
from rendering import WorldCanvas
from tools.capture_elden_vale_composition import clear_landing

DEFAULT_OUTPUT = ROOT/'docs/reviews/elden_vale_hd_integration'


def pixels(surface, mode='RGB'):
    return Image.frombytes(mode, surface.get_size(), pygame.image.tobytes(surface, mode))


def changed_pixels(first, second):
    difference = ImageChops.difference(first.convert('RGB'), second.convert('RGB'))
    raw=difference.tobytes()
    return sum(any(raw[offset:offset+3]) for offset in range(0,len(raw),3))


def gif(path, frames, duration=100):
    # One shared palette. PNG captures remain the exact render-pixel references.
    sample = Image.new('RGB', (240*min(12, len(frames)), 160))
    selected = frames[::max(1, len(frames)//12)][:12]
    for index, image in enumerate(selected):
        sample.paste(image.resize((240, 160), Image.Resampling.NEAREST), (index*240, 0))
    palette = sample.quantize(colors=256, dither=Image.Dither.NONE)
    indexed = [image.quantize(palette=palette, dither=Image.Dither.NONE) for image in frames]
    indexed[0].save(path, save_all=True, append_images=indexed[1:], duration=duration,
                    loop=0, disposal=2, optimize=False)


def view_specs(world, causeway_tile):
    """Six regional areas plus boundary/material comparisons at current coordinates."""
    views = [
        ('eldenmere_meadows', (3, -11), (3, -13), 'back'),
        ('town_miniature', (12, -25), (12, -29), 'front'),
        ('western_bridge', (-101, 29), (-109, 29), 'left'),
        ('central_causeway_reservation', causeway_tile, causeway_tile, 'front'),
        ('northern_woodland', (-48, -68), (-48, -70), 'front'),
        ('millrace_approach', (8, -60), (8, -64), 'back'),
        ('sanctuary_approach', (90, -62), (90, -66), 'back'),
        ('eastern_riverbank', (108, -27), (113, -27), 'right'),
        ('northern_checkpoint', (20, -91), (20, -94), 'back'),
        ('southern_checkpoint', (28, 91), (28, 94), 'front'),
    ]
    farms = sorted((record for record in world.region.get('setpieces', [])
                    if record.get('kind') in ('farm', 'farmstead')),
                   key=lambda record: record['tile_position'][0])
    for index, record in enumerate(farms):
        review = record.get('review', {})
        views.append((f'farmstead_{index+1}',
                      review.get('player_tile', record.get('approach_tile', record['tile_position'])),
                      review.get('focus_tile', record['tile_position']), review.get('facing', 'back')))
    for record in world.region.get('setpieces', []):
        if record.get('kind') == 'orchard':
            review = record.get('review', {})
            views.append(('southern_orchard', review.get('player_tile', record.get('approach_tile', record['tile_position'])),
                          review.get('focus_tile', record['tile_position']), review.get('facing', 'front')))
            break
    return views


def place(game, tile, *, facing='front', focus=None):
    world = game.overworld_world
    game.world = world
    game.player.position.update(clear_landing(world, tile, game.player))
    game.player.facing = facing
    game.player.moving = game.player.running = False
    game.player.walk_ms = 0
    game.map_open = False
    game.location_seconds = 0
    game.location_label = None
    game.transfer_cooldown = game.opening_fade = 0
    game.camera.reset()
    if focus is not None:
        game.camera.focus(tuple(value*24 for value in focus), duration=0)
    game.overworld_travel.update()
    assert game.world is world, ('Fixture unexpectedly transferred', tile)
    return {'requested_tile': list(tile), 'player_pixel': list(game.player.position),
            'camera_pixel': list(game.camera.position())}


def shot(game, folder, name):
    game.saves.notice_seconds = game.location_seconds = 0
    game.draw()
    image = pixels(game.window)
    assert image.size == (960, 640)
    image.save(folder/(name+'.png'))
    return image


def owner_counts(game):
    scenes = {id(scene): scene for scene in [*game.scenes.values(), game.overworld_world]}
    result = {}
    for actor in game.town.npcs:
        count = sum(actor in scene.npcs for scene in scenes.values())
        if count != 1:
            raise AssertionError(('Town actor has duplicate/lost owner', actor.data.get('id'), count))
        result[actor.data['id']] = count
    return result


def motion_capture(game, folder, running):
    place(game, (12, -23))
    start = game.player.position.copy()
    points = [pygame.Vector2(point)*24 for point in game.world.region['roads'][0]['points']]
    # Start on the south-facing main road, then follow its authored control path.
    target = min(range(len(points)), key=lambda index: points[index].distance_squared_to(start))
    frames, trace = [], []
    for tick in range(90):
        while target < len(points)-1 and game.player.position.distance_to(points[target]) < 5:
            target += 1
        direction = points[target]-game.player.position
        game.update(1/30, direction, running)
        if game.world.data['id'] != WORLD_ID or not game.world.can_stand(game.player.position):
            raise AssertionError(('Unsafe movement', running, list(game.player.position)))
        trace.append(list(game.player.position))
        if tick%3 == 0:
            game.draw();frames.append(pixels(game.window))
    displacement = game.player.position.distance_to(start)
    if displacement < (180 if running else 120):
        raise AssertionError(('Ordinary movement blocked', running, displacement))
    name = 'road_run' if running else 'road_walk'
    gif(folder/(name+'.gif'), frames)
    return {'start_pixel': list(start), 'end_pixel': list(game.player.position),
            'displacement_pixels': round(displacement, 3), 'trace_pixels': trace,
            'frames': 90, 'movement': 'Game.update at 30 Hz on existing main road'}


def town_roundtrip(game, folder):
    game.world = game.town
    game.player.position.update(TOWN_RETURN)
    game.transfer_cooldown = game.opening_fade = 0
    existing_world = game.overworld_world
    discovered_before = set(game.overworld_travel.discovered)
    game.camera.reset()
    frames, transitions = [], []
    for direction, destination in [((0, 1), WORLD_ID), ((0, -1), game.town.data['id'])]:
        for _ in range(18):
            game.update(1/30, (0, 0), False)
        for tick in range(180):
            before = game.world.data['id']
            game.update(1/30, direction, False)
            after = game.world.data['id']
            if tick%3 == 0:
                game.draw();frames.append(pixels(game.window))
            if before != after:
                transitions.append([before, after])
                if after != destination:raise AssertionError(('Wrong contact destination', transitions))
                break
        else:raise AssertionError(('Reciprocal contact did not transfer', destination))
    if len(transitions) != 2:raise AssertionError(transitions)
    if game.overworld_world is not existing_world:raise AssertionError('Regional singleton changed on town return')
    if not discovered_before <= game.overworld_travel.discovered:raise AssertionError('Discovery lost on town return')
    gif(folder/'town_roundtrip.gif', frames)
    return transitions


def density_evidence(world, folder):
    record = world._art['props']['farm_house']
    image, anchor = world._prop_image('farm_house')
    if record.get('artwork_pixels_per_world_pixel') != 2 or not isinstance(image, WorldCanvas):
        raise AssertionError('Farmhouse consumer is not native 2x art')
    native = pixels(image.native, 'RGBA')
    with Image.open(ROOT/record['image']) as opened:source = opened.convert('RGBA')
    if native.size != source.size:raise AssertionError('Native source dimensions changed')
    if native.getchannel('A').tobytes() != source.getchannel('A').tobytes():
        raise AssertionError('Native source alpha was lost')
    actual,expected=native.tobytes(),source.tobytes()
    mismatch=sum(actual[offset:offset+4]!=expected[offset:offset+4]
                 for offset in range(0,len(expected),4) if expected[offset+3])
    if mismatch:raise AssertionError(('Source sprite pixels lost in normalization', mismatch))
    with Image.open(ROOT/'assets/terrain/overworld/elden_vale/polish/props/farm_house.png') as opened:
        legacy = opened.convert('RGBA').resize(native.size, Image.Resampling.NEAREST)
    native.save(folder/'farmhouse_native_pixels.png')
    legacy.save(folder/'farmhouse_legacy_upscale.png')
    # This proves fine texels survive the actual chunk compositor as well.
    cx, cy = math.floor(world.town_exit[0]/CHUNK_PIXELS), math.floor((world.town_exit[1]+192)/CHUNK_PIXELS)
    chunk = world._render_chunk(cx, cy)
    if not isinstance(chunk, WorldCanvas):raise AssertionError('HD map produced a legacy-only ground chunk')
    native_chunk = pixels(chunk.native)
    mirror = pixels(chunk).resize(native_chunk.size, Image.Resampling.NEAREST)
    changed = changed_pixels(native_chunk, mirror)
    if changed == 0:raise AssertionError('Chunk discarded sub-logical source detail')
    native_chunk.crop((0,0,256,256)).save(folder/'ground_native_detail.png')
    mirror.crop((0,0,256,256)).save(folder/'ground_logical_upscale.png')
    return {'prop_key': 'farm_house', 'source_image': record['image'],
            'logical_size': list(image.get_size()), 'native_size': list(image.native.get_size()),
            'logical_foot_anchor': list(anchor), 'source_visible_pixel_mismatches': mismatch,
            'changed_pixels_against_legacy_upscale': changed_pixels(native, legacy),
            'chunk_coord': [cx,cy], 'native_chunk_pixels_different_from_mirror_upscale': changed}


def water_capture(game, folder):
    world = game.overworld_world
    camera = (-122*24-240, -10*24-160)
    hidden = SimpleNamespace(position=pygame.Vector2(), story_visible=False)
    report = {}
    for reduced in (False, True):
        game.audio.set_reduced_motion(reduced)
        game.update(.04, (0,0), False)
        # Game.draw publishes the setting to the active regional renderer.
        game.draw()
        frames = []
        for elapsed in (0, 200, 400):
            target = WorldCanvas((480,320))
            world.draw(target, camera, hidden, elapsed, include_ui=False)
            frame = pixels(target.native)
            frame.save(folder/(f'water_{"still" if reduced else "animated"}_{elapsed}.png'))
            frames.append(frame)
        crop = (416,192,544,448)
        differences = [changed_pixels(frames[0].crop(crop), frame.crop(crop)) for frame in frames[1:]]
        if (not reduced and not any(differences)) or (reduced and any(differences)):
            raise AssertionError(('Water temporal/reduced-motion contract failed', reduced, differences))
        report['reduced' if reduced else 'normal'] = {'camera_pixel': list(camera),
            'native_water_crop': list(crop), 'changed_pixels_vs_0ms': differences}
    game.audio.set_reduced_motion(False)
    game.update(.04, (0,0), False)
    return report


def freeze_capture(game):
    place(game,(12,-23))
    world=game.overworld_world
    report={}
    def state():
        return {'elapsed_ms':game.elapsed_ms,'position':list(game.player.position),
                'farm':world.grain_farm.to_dict(),'garden':world.garden_orchard.to_dict(),
                'bridge':world.bridge_crew.to_dict()}
    def rendered():
        canvas=WorldCanvas((480,320))
        world.draw(canvas,game.camera.position(),game.player,game.elapsed_ms,False)
        return hashlib.sha256(pygame.image.tobytes(canvas.native,'RGB')).hexdigest()
    for mode in ('pause','focus_loss'):
        game.draw()
        before=copy.deepcopy(state());before_image=rendered()
        if mode=='pause':game.pause.open()
        else:game.handle_events([pygame.event.Event(pygame.WINDOWFOCUSLOST)])
        game.update(.5,(1,0),True)
        after=state();same_image=before_image==rendered()
        if before!=after or not same_image:raise AssertionError(('Exploration did not freeze',mode))
        report[mode]={'frozen_elapsed_ms':before['elapsed_ms'],'frozen_position':before['position'],
                      'controller_state_preserved':True,'native_render_unchanged':same_image}
        if mode=='pause':game.pause.close()
        else:game.handle_events([pygame.event.Event(pygame.WINDOWFOCUSGAINED)])
        game.update(.1,(0,0),False)
        if game.elapsed_ms<=before['elapsed_ms']:raise AssertionError(('Exploration failed to resume',mode))
    return report


def save_continue(game, temporary):
    place(game, (3, -11))
    before_quests = copy.deepcopy(game.quests.to_dict())
    owners = owner_counts(game)
    expected = game.journey_snapshot()
    if not game.save_progress():raise AssertionError(('Save failed', game.save_error))
    restored = Game(window_size=(960,640), fullscreen=False, start_on_title=True,
                    save_path=temporary/'journey.json', settings_path=temporary/'settings.json')
    restored.audio.set_music(0);restored.audio.set_effects(0)
    if not restored.has_saved_journey or not restored.begin_journey(True):
        raise AssertionError('Saved regional journey could not Continue')
    actual = restored.journey_snapshot()
    for key in ('quests','party','dialogue_flags','player','overworld'):
        if actual[key] != expected[key]:raise AssertionError(('Continue state changed',key))
    if restored.quests.to_dict() != before_quests:raise AssertionError('Quest changed on Continue')
    if owner_counts(restored) != owners:raise AssertionError('Actor owners changed on Continue')
    restored.music.stop()
    return {'scene': actual['player']['scene'], 'position': actual['player']['position'],
            'exact_snapshot_keys_preserved': ['quests','party','dialogue_flags','player','overworld'],
            'town_actor_owners': owners}


def capture(folder=DEFAULT_OUTPUT, *, stills_only=False, causeway_tile=(-3,8)):
    folder.mkdir(parents=True, exist_ok=True)
    report = {'fixture': 'Disposable initialized Game exploration; no seeded quest progression. Fixed views position player on clear ground; motion/transfers use actual Game.update.',
              'actual_renderer': True, 'display_size': [960,640], 'views': {},
              'profile_scope': 'Warm production world renderer only, SDL dummy; excludes simulation/display/UI. Hardware-specific.'}
    timings = {}
    with tempfile.TemporaryDirectory(prefix='elden-vale-hd-integration-') as directory:
        temporary = Path(directory)
        game = Game(window_size=(960,640), fullscreen=False, start_on_title=True,
                    save_path=temporary/'journey.json', settings_path=temporary/'settings.json')
        try:
            game.on_title = False
            game.opening.restore({'version':1,'stage':'disabled'})
            game.opening_fade = game.transfer_cooldown = 0
            game.audio.set_music(0);game.audio.set_effects(0)
            world = game.overworld_world
            report['rss_after_initialized_game_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            report['registry'] = {key:value for key,value in world.region.items()
                                  if 'art_manifest' in key or 'hd' in key or 'reservation' in key}
            report['registry_record_counts_by_density'] = {
                group: {str(density): sum(record.get('artwork_pixels_per_world_pixel',1)==density
                                         for record in world._art.get(group,{}).values())
                        for density in (1,2)} for group in ('tiles','props')}
            input_paths = {world.path, Path(__file__).resolve(), ROOT/'main.py',
                           ROOT/'overworld_world.py', ROOT/'overworld_environment.py'}
            input_paths.update(ROOT/value for key,value in world.region.items()
                               if 'art_manifest' in key and isinstance(value,str) and (ROOT/value).exists())
            input_paths.update(ROOT/record['image'] for group in ('tiles','props')
                               for record in world._art.get(group,{}).values() if record.get('image'))
            helper=ROOT/'regional_terrain_hd.py'
            if helper.exists():input_paths.add(helper)
            input_hashes={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()
                          for path in sorted(input_paths)}
            report['region_sha256'] = hashlib.sha256(world.path.read_bytes()).hexdigest()
            quest_before = copy.deepcopy(game.quests.to_dict())
            for name, player, focus, facing in view_specs(world,causeway_tile):
                report['views'][name] = place(game,player,facing=facing,focus=focus)
                shot(game,folder,name)
                canvas = WorldCanvas((480,320))
                stable=0
                for warmup in range(64):
                    before=set(world._render_cache.items)
                    world.draw(canvas,game.camera.position(),game.player,game.elapsed_ms,False)
                    stable=stable+1 if set(world._render_cache.items)==before else 0
                    if stable>=3:break
                else:raise AssertionError('Lookahead ring did not reach a cache-stable warm state')
                samples=[]
                for _ in range(12):
                    start=perf_counter();world.draw(canvas,game.camera.position(),game.player,game.elapsed_ms,False)
                    samples.append((perf_counter()-start)*1000)
                stats=world.cache_stats
                if stats['render_bytes'] > world._render_cache.limit:raise AssertionError('Render cache exceeded budget')
                if stats['metadata_chunks'] > world._metadata_cache.limit:raise AssertionError('Metadata cache exceeded budget')
                timings[name]={'cache_stable_warmup_draws':warmup+1,'warm_draw_ms_mean':sum(samples)/len(samples),'warm_draw_ms_max':max(samples),
                               'cache':stats,'render_budget_bytes':world._render_cache.limit}
                print(f'Captured {name}',flush=True)
            report['rss_after_static_views_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            report['native_detail'] = density_evidence(world,folder)
            game.audio.set_reduced_motion(True)
            report['views']['reduced_motion'] = place(game,(108,-27),focus=(113,-27))
            game.update(.04,(0,0),False);shot(game,folder,'reduced_motion')
            game.audio.set_reduced_motion(False)
            if not stills_only:
                report['road_walk'] = motion_capture(game,folder,False)
                report['road_run'] = motion_capture(game,folder,True)
                report['town_roundtrip'] = town_roundtrip(game,folder)
                place(game,(108,-27),focus=(113,-27))
                report['water'] = water_capture(game,folder)
                report['freeze_resume'] = freeze_capture(game)
                report['save_continue'] = save_continue(game,temporary)
            if game.quests.to_dict() != quest_before:raise AssertionError('Review advanced quest progress')
            for relative,digest in input_hashes.items():
                if hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()!=digest:
                    raise AssertionError(('Render input changed during capture; rerun',relative))
            report['render_input_sha256']=input_hashes
            report['timings']=timings
            report['cache_final']=world.cache_stats
            report['peak_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            report['peak_rss_scope']='Whole capture process: Game asset banks/caches, GIF construction and second initialized Game for Continue; not just regional renderer memory.'
            report['captures']={path.name:hashlib.sha256(path.read_bytes()).hexdigest()
                                for path in sorted(folder.iterdir()) if path.suffix in ('.png','.gif')}
            (folder/'observations.json').write_text(json.dumps(report,indent=2)+'\n')
        finally:
            game.music.stop();pygame.quit();gc.collect()
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',nargs='?',type=Path,default=DEFAULT_OUTPUT)
    parser.add_argument('--stills-only',action='store_true')
    parser.add_argument('--causeway-tile',nargs=2,type=float,default=(-3,8))
    args=parser.parse_args()
    capture(args.output,stills_only=args.stills_only,causeway_tile=tuple(args.causeway_tile))
