"""Capture the integrated well through actual Game updates and native rendering.

Only the initial long rest is omitted. The actor follows its live navigation;
the helper never advances the well separately or signals station readiness.
All saves/settings live in a disposable directory.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw, ImageSequence
import pygame
from main import Game, Gardener, VIEW_SIZE
from rendering import snapshot

OUTPUT = ROOT/'docs/reviews/well_live'
DT = .1
WELL_CAMERA = (456, 778)
WELL_CROP = (0, 0, 360, 300)


def digest(raw):
    return sha256(raw).hexdigest()


def document(value):
    return (json.dumps(value, indent=2, allow_nan=False)+'\n').encode()


def render(game, camera):
    """The production World compositor, preserving its 960x640 native buffer."""
    game.canvas.reset_detail()
    game.world.draw(game.canvas, camera, game.player, game.elapsed_ms, include_ui=False)
    image = snapshot(game.canvas)
    return Image.frombytes('RGBA', image.get_size(), pygame.image.tobytes(image, 'RGBA')).convert('RGB')


def labelled(image, title, caption):
    board = Image.new('RGB', (image.width, image.height+46), '#213c35')
    board.paste(image, (0, 46))
    draw = ImageDraw.Draw(board)
    draw.text((8, 6), title, fill='#f1e6c8')
    draw.text((8, 25), caption, fill='#b9cfbd')
    return board


def animation(path, frames, duration_ms):
    """Use one palette to avoid per-frame color changes; PNGs retain exact RGB."""
    if not frames:
        raise AssertionError('Cannot export an empty runtime excerpt: '+str(path))
    samples = frames[::max(1, len(frames)//32)]
    atlas = Image.new('RGB', (160*8, 120*((len(samples)+7)//8)))
    for index, frame in enumerate(samples):
        atlas.paste(frame.resize((160, 120), Image.Resampling.NEAREST), ((index%8)*160, (index//8)*120))
    palette = atlas.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    indexed = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
    indexed[0].save(path, save_all=True, append_images=indexed[1:], duration=duration_ms,
                    loop=0, disposal=1, optimize=True)
    with Image.open(path) as saved:
        total = 0
        cursor = 0
        for frame in ImageSequence.Iterator(saved):
            duration = frame.info.get('duration', 0)
            total += duration
            rgb = frame.convert('RGB').tobytes()
            if duration % duration_ms:
                raise AssertionError('GIF sample duration changed: '+str(path))
            for _ in range(duration//duration_ms):
                if cursor >= len(indexed) or indexed[cursor].convert('RGB').tobytes() != rgb:
                    raise AssertionError('GIF encoding changed its quantized runtime frame: '+str(path))
                cursor += 1
        if cursor != len(indexed):
            raise AssertionError('GIF frame count changed: '+str(path))
    expected = len(frames)*duration_ms
    if total != expected:
        raise AssertionError(f'GIF timing changed for {path}: {total} != {expected}')
    return {'source_samples':len(frames), 'duration_ms':total, 'sample_duration_ms':duration_ms}


def capture(output=OUTPUT):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    map_path = 'assets/maps/eldenmere/playable/map.json'
    map_data = json.loads((ROOT/map_path).read_text())
    preserved_paths = [map_path, map_data['collision'], 'assets/maps/eldenmere/routines/gardener.json']
    for key in ('navigation', 'nav_mask', 'navmesh'):
        path = map_data.get(key)
        if isinstance(path, str) and (ROOT/path).is_file():preserved_paths.append(path)
    before = {relative:digest((ROOT/relative).read_bytes()) for relative in preserved_paths}
    sources = ['main.py', 'npc_routines.py', 'well_routine.py', 'well_mechanism.py',
               'well_mechanism_presentation.py', 'tools/capture_well_live.py']
    for optional in ('gardener_well_runtime.py', 'well_live_presentation.py'):
        if (ROOT/optional).is_file():sources.append(optional)
    source_before = {path:digest((ROOT/path).read_bytes()) for path in sources}
    well_frames, route_frames, pour_frames, pickup_frames = [], [], [], []
    trace, phase_stills, route_stills = [], {}, {}
    cue_frames, contact_frames = {}, {'lower':{}, 'raise':{}}
    gif_report = {}
    with tempfile.TemporaryDirectory(prefix='well-live-review-') as temporary:
        temporary = Path(temporary)
        game = Game(fullscreen=False, start_on_title=False,
                    save_path=temporary/'save.json', settings_path=temporary/'settings.json')
        game.opening.stage = 'disabled'
        game.player.position.update(520, 520)
        index = next(i for i, actor in enumerate(game.town.npcs) if actor.data['id']=='sanctuary_gardener')
        actor = Gardener(game.town.npcs[index].data, game.town, random.Random(2026))
        game.town.npcs[index] = actor
        game.update(max(0, actor.rest_remaining_ms-1000)/1000, (0, 0), False)
        start_ms = game.elapsed_ms
        finished_ms = None
        route_clear = True
        previous_position = actor.position.copy()
        max_step = 0.
        depth_done = False
        for tick in range(1800):
            state = actor.state
            mechanism = game.town.well.snapshot()
            selection = actor.presentation_selection()
            max_step = max(max_step, actor.position.distance_to(previous_position))
            previous_position.update(actor.position)
            clear = game.town.can_stand(actor.position, actor.probe_size, actor,
                                        game.town.probe_rect(game.player.position))
            route_clear = route_clear and clear
            if not clear:
                raise AssertionError(f'Live gardener route blocked at {state}: {tuple(actor.position)}')
            trace.append({
                'review_ms':round(game.elapsed_ms-start_ms, 6), 'actor_state':state,
                'actor_position_world':list(actor.position), 'facing':actor.facing,
                'water_units':actor.water_units, 'pail_location':actor.pail_location,
                'pose_id':selection.get('pose_id'), 'pail_visible':selection.get('pail_visible'),
                'well':mechanism.to_dict(),
            })
            if tick%5 == 0:
                camera = (max(0, round(actor.position.x)-120), max(0, round(actor.position.y)-80))
                route_frames.append(labelled(render(game, camera).crop((0, 0, 480, 320)),
                                             'LIVE GAME / complete watering trip',
                                             f'{state} | water {actor.water_units}/6 | 0.5s samples'))
            near_well = actor.position.distance_to((528, 894)) < 110
            if state.startswith('well_') or near_well and state in ('to_well', 'return_to_sanctuary'):
                crop = render(game, WELL_CAMERA).crop(WELL_CROP)
                caption = f'{mechanism.phase_id} | {mechanism.pail_owner} | water {actor.water_units}/6'
                well_frames.append(labelled(crop, 'LIVE GAME / well operation', caption))
                phase = mechanism.phase_id
                if phase in ('attach', 'detach'):
                    cue = .7 if phase == 'attach' else .65
                    side = 'before' if mechanism.phase_progress < cue else 'after'
                    if side == 'before' or (phase, side) not in cue_frames:
                        cue_frames[phase, side] = labelled(crop, phase+' / '+side+' cue', caption)
                if phase in contact_frames and mechanism.crank_sample not in contact_frames[phase]:
                    contact_frames[phase][mechanism.crank_sample] = labelled(
                        crop.crop((150, 90, 290, 235)),
                        phase+' / crank '+str(mechanism.crank_sample), selection['pose_id'])
                if mechanism.phase_id not in phase_stills:
                    phase_stills[mechanism.phase_id] = tick
                    render(game, (288, 660)).save(output/f'phase_{mechanism.phase_id}.png')
                if mechanism.phase_id == 'fill' and not depth_done:
                    player_position = game.player.position.copy()
                    for name, position in (('north', (528, 828)), ('south', (528, 912))):
                        game.player.position.update(position)
                        render(game, (288, 660)).save(output/f'depth_{name}.png')
                    game.player.position.update(player_position)
                    normal_state = mechanism.to_dict()
                    game.town.reduced_motion = True
                    render(game, (288, 660)).save(output/'reduced_motion_fill.png')
                    game.town.reduced_motion = False
                    if game.town.well.snapshot().to_dict() != normal_state:
                        raise AssertionError('Reduced-motion rendering advanced the mechanism')
                    depth_done = True
            if state.startswith('water_'):
                camera = (round(actor.position.x)-80, round(actor.position.y)-60)
                crop = render(game, camera).crop((0, 0, 320, 200))
                pour_frames.append(labelled(crop, 'LIVE GAME / watering', f'{state} | water {actor.water_units}/6'))
                if selection.get('effect') == 'pour' and state not in route_stills:
                    route_stills[state] = tick
                    render(game, camera).save(output/(state+'.png'))
            if state in ('pickup', 'setdown'):
                camera = (round(actor.position.x)-80, round(actor.position.y)-60)
                pickup_frames.append(labelled(render(game, camera).crop((0, 0, 320, 200)),
                                               'LIVE GAME / pail handling', state))
            if actor.completed_cycles:
                if finished_ms is None:
                    finished_ms = game.elapsed_ms
                    render(game, (180, 190)).save(output/'completed_at_rest.png')
                if game.elapsed_ms-finished_ms >= 800:
                    break
            game.update(DT, (0, 0), False)
        else:
            raise AssertionError(f'The actual Game routine did not complete: {actor.state}')
        if actor.watered_beds != [bed['id'] for bed in actor.behavior['beds']]:
            raise AssertionError('The live trip did not water all six targets in order')
        if actor.water_units != 0 or actor.pail_location != 'rest':
            raise AssertionError('The live trip did not leave one empty pail at rest')
        events = [dict(event) for event in actor.events]
        well_events = [event.to_dict() for event in actor.well_events]
        identity = {'roster_design':getattr(getattr(actor, 'roster_art', None), 'design_id', None),
                    'animation_path':actor.animation_path, 'draw_anchor_logical':list(actor.draw_anchor),
                    'probe_size_logical':list(actor.probe_size)}
        active_duration = finished_ms-start_ms
        game.music.stop()
        pygame.quit()
    handoff = Image.new('RGB', (720, 692), '#213c35')
    for index, key in enumerate((('attach', 'before'), ('attach', 'after'),
                                 ('detach', 'before'), ('detach', 'after'))):
        if key not in cue_frames:
            raise AssertionError('Actual trace did not bracket ownership cue: '+str(key))
        handoff.paste(cue_frames[key], ((index%2)*360, (index//2)*346))
    handoff.save(output/'handoff_cues.png')
    contacts = Image.new('RGB', (560, 8*191), '#213c35')
    for row, family in enumerate(('lower', 'raise')):
        if set(contact_frames[family]) != set(range(16)):
            raise AssertionError('Actual trace missed crank samples: '+family)
        for sample, image in contact_frames[family].items():
            index = row*16+sample
            contacts.paste(image, ((index%4)*140, (index//4)*191))
    contacts.save(output/'operating_contacts.png')
    for name, frames, duration in (
        ('well_operation.gif', well_frames, 100),
        ('well_operation_slow.gif', well_frames, 200),
        ('complete_trip.gif', route_frames, 500),
        ('watering.gif', pour_frames, 100),
        ('pickup_setdown.gif', pickup_frames, 100),
    ):
        gif_report[name] = animation(output/name, frames, duration)
    for relative, value in before.items():
        if digest((ROOT/relative).read_bytes()) != value:
            raise AssertionError('Capture changed source data: '+relative)
    for relative, value in source_before.items():
        if digest((ROOT/relative).read_bytes()) != value:
            raise AssertionError('Runtime source changed during capture; regenerate after freeze: '+relative)
    report = {
        'scope':'Actual Game simulation and production native World compositor, with disposable saves/settings.',
        'revision':subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'runtime_activation':True, 'step_ms':100,
        'initial_rest_omitted':True, 'active_review_duration_ms':active_duration,
        'completed_cycles':actor.completed_cycles, 'watered_beds':actor.watered_beds,
        'remaining_water_units':actor.water_units, 'final_pail_location':actor.pail_location,
        'identity':identity, 'live_route_clear_at_every_sample':route_clear,
        'maximum_sample_step_logical':max_step, 'events':events, 'well_events':well_events,
        'native_viewport_size':[2*v for v in VIEW_SIZE],
        'gif_sampling':'Native crops; full trip sampled every500ms. Common256-color GIF palette approximates some colors; PNGs retain native RGB.',
        'watering_montage':'Only watering actions are retained; travel between garden stops is omitted from this excerpt.',
        'pickup_montage':'Pickup and setdown only; the complete trip appears separately.',
        'depth_fixture':'Only diagnostic north/south stills reposition the disposable player; normal route simulation is untouched.',
        'source_sha256':source_before,
        'preserved_source_sha256':before, 'gifs':gif_report,
        'samples':trace,
        'artifact_sha256':{path.name:digest(path.read_bytes()) for path in sorted(output.iterdir()) if path.suffix in ('.png', '.gif')},
    }
    (output/'observations.json').write_bytes(document(report))
    print(f'Live well capture: {len(trace)} Game samples; six targets; {active_duration/1000:.2f}s active review.')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', nargs='?', type=Path, default=OUTPUT)
    capture(parser.parse_args().output)
